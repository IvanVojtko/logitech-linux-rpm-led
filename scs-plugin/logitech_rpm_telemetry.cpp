// SPDX-License-Identifier: GPL-3.0-only

#ifdef _WIN32
#  define WINVER 0x0501
#  define _WIN32_WINNT 0x0501
#  include <winsock2.h>
#  include <ws2tcpip.h>
#else
#  include <arpa/inet.h>
#  include <sys/socket.h>
#  include <unistd.h>
#endif

#include <cstring>

#include "scssdk_telemetry.h"
#include "eurotrucks2/scssdk_eut2.h"
#include "eurotrucks2/scssdk_telemetry_eut2.h"

namespace {

constexpr unsigned short kUdpPort = 5607;
constexpr char kPacketMagic[4] = {'L', 'R', 'P', 'M'};
constexpr unsigned char kPacketVersion = 1;

#pragma pack(push, 1)
struct rpm_packet_t
{
	char magic[4];
	unsigned char version;
	unsigned char running;
	unsigned short reserved;
	float current_rpm;
	float max_rpm;
};
#pragma pack(pop)

float current_rpm = 0.0f;
float max_rpm = 0.0f;
bool telemetry_running = false;
scs_log_t game_log = nullptr;

#ifdef _WIN32
SOCKET udp_socket = INVALID_SOCKET;
#else
int udp_socket = -1;
#endif

sockaddr_in udp_destination {};

void log_message(const scs_log_type_t type, const char *const text)
{
	if (game_log) {
		game_log(type, text);
	}
}

bool initialize_udp()
{
#ifdef _WIN32
	WSADATA wsa_data;
	if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
		return false;
	}
	udp_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
	if (udp_socket == INVALID_SOCKET) {
		WSACleanup();
		return false;
	}
#else
	udp_socket = socket(AF_INET, SOCK_DGRAM, 0);
	if (udp_socket < 0) {
		return false;
	}
#endif

	std::memset(&udp_destination, 0, sizeof(udp_destination));
	udp_destination.sin_family = AF_INET;
	udp_destination.sin_port = htons(kUdpPort);
	udp_destination.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	return true;
}

void shutdown_udp()
{
#ifdef _WIN32
	if (udp_socket != INVALID_SOCKET) {
		closesocket(udp_socket);
		udp_socket = INVALID_SOCKET;
	}
	WSACleanup();
#else
	if (udp_socket >= 0) {
		close(udp_socket);
		udp_socket = -1;
	}
#endif
}

void send_rpm_packet()
{
#ifdef _WIN32
	if (udp_socket == INVALID_SOCKET) {
		return;
	}
#else
	if (udp_socket < 0) {
		return;
	}
#endif

	rpm_packet_t packet {};
	std::memcpy(packet.magic, kPacketMagic, sizeof(packet.magic));
	packet.version = kPacketVersion;
	packet.running = telemetry_running ? 1 : 0;
	packet.current_rpm = current_rpm;
	packet.max_rpm = max_rpm;

	sendto(
		udp_socket,
		reinterpret_cast<const char *>(&packet),
		sizeof(packet),
		0,
		reinterpret_cast<const sockaddr *>(&udp_destination),
		sizeof(udp_destination)
	);
}

const scs_named_value_t *find_attribute(
	const scs_telemetry_configuration_t &configuration,
	const char *const name,
	const scs_value_type_t expected_type
)
{
	for (const scs_named_value_t *current = configuration.attributes; current->name; ++current) {
		if ((current->index != SCS_U32_NIL) || (std::strcmp(current->name, name) != 0)) {
			continue;
		}
		if (current->value.type == expected_type) {
			return current;
		}
		return nullptr;
	}
	return nullptr;
}

SCSAPI_VOID telemetry_pause(
	const scs_event_t event,
	const void *const,
	const scs_context_t
)
{
	telemetry_running = (event == SCS_TELEMETRY_EVENT_started);
	if (!telemetry_running) {
		current_rpm = 0.0f;
	}
	send_rpm_packet();
}

SCSAPI_VOID telemetry_configuration(
	const scs_event_t,
	const void *const event_info,
	const scs_context_t
)
{
	const auto *const info = static_cast<const scs_telemetry_configuration_t *>(event_info);
	if (std::strcmp(info->id, SCS_TELEMETRY_CONFIG_truck) != 0) {
		return;
	}

	const scs_named_value_t *const rpm_limit = find_attribute(
		*info,
		SCS_TELEMETRY_CONFIG_ATTRIBUTE_rpm_limit,
		SCS_VALUE_TYPE_float
	);
	max_rpm = rpm_limit ? rpm_limit->value.value_float.value : 0.0f;
	send_rpm_packet();
}

SCSAPI_VOID telemetry_store_rpm(
	const scs_string_t,
	const scs_u32_t,
	const scs_value_t *const value,
	const scs_context_t
)
{
	if (!value || value->type != SCS_VALUE_TYPE_float) {
		current_rpm = 0.0f;
	} else {
		current_rpm = value->value_float.value;
	}
	send_rpm_packet();
}

} // namespace

SCSAPI_RESULT scs_telemetry_init(
	const scs_u32_t version,
	const scs_telemetry_init_params_t *const params
)
{
	if (version != SCS_TELEMETRY_VERSION_1_01) {
		return SCS_RESULT_unsupported;
	}

	const auto *const version_params = static_cast<const scs_telemetry_init_params_v101_t *>(params);
	game_log = version_params->common.log;

	if (std::strcmp(version_params->common.game_id, SCS_GAME_ID_EUT2) != 0) {
		log_message(SCS_LOG_TYPE_warning, "Logitech RPM telemetry plugin loaded by a non-ETS2/ATS SCS game.");
	}

	if (!initialize_udp()) {
		log_message(SCS_LOG_TYPE_error, "Logitech RPM telemetry plugin failed to open UDP socket.");
		game_log = nullptr;
		return SCS_RESULT_generic_error;
	}

	const bool events_registered =
		(version_params->register_for_event(SCS_TELEMETRY_EVENT_paused, telemetry_pause, nullptr) == SCS_RESULT_ok) &&
		(version_params->register_for_event(SCS_TELEMETRY_EVENT_started, telemetry_pause, nullptr) == SCS_RESULT_ok) &&
		(version_params->register_for_event(SCS_TELEMETRY_EVENT_configuration, telemetry_configuration, nullptr) == SCS_RESULT_ok);
	if (!events_registered) {
		shutdown_udp();
		game_log = nullptr;
		return SCS_RESULT_generic_error;
	}

	version_params->register_for_channel(
		SCS_TELEMETRY_TRUCK_CHANNEL_engine_rpm,
		SCS_U32_NIL,
		SCS_VALUE_TYPE_float,
		SCS_TELEMETRY_CHANNEL_FLAG_no_value,
		telemetry_store_rpm,
		nullptr
	);

	current_rpm = 0.0f;
	max_rpm = 0.0f;
	telemetry_running = false;
	send_rpm_packet();
	log_message(SCS_LOG_TYPE_message, "Logitech RPM telemetry plugin initialized.");
	return SCS_RESULT_ok;
}

SCSAPI_VOID scs_telemetry_shutdown(void)
{
	telemetry_running = false;
	current_rpm = 0.0f;
	send_rpm_packet();
	shutdown_udp();
	game_log = nullptr;
}
