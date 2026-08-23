APP_NAME := logitech-rpm-indicator
DESKTOP_ID := io.github.IvanVojtko.LogitechRpmIndicator

PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
LIBDIR ?= $(PREFIX)/lib
DATADIR ?= $(PREFIX)/share
APPDIR ?= $(LIBDIR)/$(APP_NAME)
DOCDIR ?= $(DATADIR)/doc/$(APP_NAME)

INSTALL ?= install
PYTHON ?= python3
PYTHON_EXECUTABLE ?= /usr/bin/python3

.PHONY: all check install uninstall update-desktop-caches test \
	build-ets2-plugin-linux build-ets2-plugin-windows build-assetto-wrapper \
	clean

all:
	@printf 'This is a Python application. Run "make install" to install it.\n'

check:
	$(PYTHON) -m py_compile main.py games/*.py wheels/*.py
	@if command -v desktop-file-validate >/dev/null 2>&1; then \
		desktop-file-validate packaging/$(DESKTOP_ID).desktop; \
	fi
	@test -s icons/$(APP_NAME).png
	@test -s icons/$(APP_NAME).svg

test:
	$(PYTHON) -m pytest

install: check
	$(INSTALL) -d \
		$(DESTDIR)$(BINDIR) \
		$(DESTDIR)$(APPDIR)/games \
		$(DESTDIR)$(APPDIR)/installers \
		$(DESTDIR)$(APPDIR)/wheels \
		$(DESTDIR)$(APPDIR)/icons \
		$(DESTDIR)$(APPDIR)/assetto-wrapper \
		$(DESTDIR)$(APPDIR)/scs-plugin \
		$(DESTDIR)$(DATADIR)/applications \
		$(DESTDIR)$(DOCDIR) \
		$(DESTDIR)$(DATADIR)/icons/hicolor/256x256/apps \
		$(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps
	sed \
		-e 's|@APPDIR@|$(APPDIR)|g' \
		-e 's|@PYTHON_EXECUTABLE@|$(PYTHON_EXECUTABLE)|g' \
		packaging/$(APP_NAME).in > $(DESTDIR)$(BINDIR)/$(APP_NAME)
	chmod 0755 $(DESTDIR)$(BINDIR)/$(APP_NAME)
	$(INSTALL) -m 0644 main.py $(DESTDIR)$(APPDIR)/
	$(INSTALL) -m 0644 games/*.py $(DESTDIR)$(APPDIR)/games/
	$(INSTALL) -m 0644 installers/*.py $(DESTDIR)$(APPDIR)/installers/
	$(INSTALL) -m 0644 wheels/*.py $(DESTDIR)$(APPDIR)/wheels/
	$(INSTALL) -m 0644 icons/* $(DESTDIR)$(APPDIR)/icons/
	$(INSTALL) -m 0644 assetto-wrapper/Makefile assetto-wrapper/*.c \
		$(DESTDIR)$(APPDIR)/assetto-wrapper/
	if [ -f "assetto-wrapper/acpmf_wrapper.exe" ]; then \
		$(INSTALL) -m 0755 "assetto-wrapper/acpmf_wrapper.exe" \
			$(DESTDIR)$(APPDIR)/assetto-wrapper/; \
	fi;
	$(INSTALL) -m 0644 scs-plugin/Makefile scs-plugin/*.cpp \
		$(DESTDIR)$(APPDIR)/scs-plugin/
	@for plugin in scs-plugin/*.so scs-plugin/*.dll; do \
		if [ -f "$$plugin" ]; then \
			$(INSTALL) -m 0755 "$$plugin" $(DESTDIR)$(APPDIR)/scs-plugin/; \
		fi; \
	done
	$(INSTALL) -m 0644 packaging/$(DESKTOP_ID).desktop \
		$(DESTDIR)$(DATADIR)/applications/
	$(INSTALL) -m 0644 icons/$(APP_NAME).png \
		$(DESTDIR)$(DATADIR)/icons/hicolor/256x256/apps/
	$(INSTALL) -m 0644 icons/$(APP_NAME).svg \
		$(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/
	$(INSTALL) -m 0644 README.md LICENSE $(DESTDIR)$(DOCDIR)/
	@if [ -z "$(DESTDIR)" ]; then $(MAKE) update-desktop-caches; fi

uninstall:
	rm -f \
		$(DESTDIR)$(BINDIR)/$(APP_NAME) \
		$(DESTDIR)$(DATADIR)/applications/$(DESKTOP_ID).desktop \
		$(DESTDIR)$(DATADIR)/icons/hicolor/256x256/apps/$(APP_NAME).png \
		$(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps/$(APP_NAME).svg
	rm -rf $(DESTDIR)$(APPDIR) $(DESTDIR)$(DOCDIR)
	@if [ -z "$(DESTDIR)" ]; then $(MAKE) update-desktop-caches; fi

update-desktop-caches:
	@if command -v update-desktop-database >/dev/null 2>&1; then \
		update-desktop-database -q $(DATADIR)/applications || true; \
	fi
	@if command -v gtk-update-icon-cache >/dev/null 2>&1; then \
		gtk-update-icon-cache -q -t -f $(DATADIR)/icons/hicolor || true; \
	fi

build-ets2-plugin-linux:
	$(MAKE) -C scs-plugin linux

build-ets2-plugin-windows:
	$(MAKE) -C scs-plugin windows

build-assetto-wrapper:
	$(MAKE) -C assetto-wrapper

clean:
	$(MAKE) -C scs-plugin clean
	$(MAKE) -C assetto-wrapper clean
