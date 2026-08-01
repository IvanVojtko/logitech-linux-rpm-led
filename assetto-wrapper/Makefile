MINGW_x86_64 = x86_64-w64-mingw32
MINGW_i686 = i686-w64-mingw32

.DEFAULT_GOAL = acpmf_wrapper.exe
.PHONY: clean

acpmf_wrapper.exe: acpmf_wrapper.c
	$(MINGW_x86_64)-gcc $< -o $@ -O0 -msse2 # -shared-libgcc
# Comment to keep debug symbols
	$(MINGW_x86_64)-strip --strip-unneeded $@ 

# 32 bit version
acpmf_wrapper_x86.exe: acpmf_wrapper.c
	$(MINGW_i686)-gcc $< -o $@ -O0 -msse2 # -shared-libgcc
# Comment to keep debug symbols
	$(MINGW_i686)-strip --strip-unneeded $@

clean:
	@rm -vf acpmf_wrapper.exe acpmf_wrapper_x86.exe
