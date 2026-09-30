WAILS := go run github.com/wailsapp/wails/v2/cmd/wails@v2.16.0
TAGS ?= webkit2_41
NATIVE_DEPS := .native-deps/root

# CI/containers sometimes have the WebKitGTK runtime installed without its
# development symlinks and pkg-config files.  Keep a user-local fallback so a
# reboot cannot invalidate builds by clearing a directory under /tmp.
ifeq ($(shell pkg-config --exists webkit2gtk-4.1 && echo yes),)
PKG_CONFIG_PATH := $(CURDIR)/$(NATIVE_DEPS)/usr/lib/x86_64-linux-gnu/pkgconfig:$(CURDIR)/$(NATIVE_DEPS)/usr/share/pkgconfig$(if $(PKG_CONFIG_PATH),:$(PKG_CONFIG_PATH))
CGO_LDFLAGS := -L$(CURDIR)/$(NATIVE_DEPS)/usr/lib/x86_64-linux-gnu$(if $(CGO_LDFLAGS), $(CGO_LDFLAGS))
export PKG_CONFIG_PATH
export CGO_LDFLAGS
endif

.PHONY: build dev test frontend clean native-deps
native-deps:
	./scripts/prepare-native-deps.sh
build: native-deps
	$(WAILS) build -tags $(TAGS)
dev: native-deps
	$(WAILS) dev -tags $(TAGS)
frontend:
	cd frontend && npm ci && npm run build
test:
	go test -race ./internal/...
	cd frontend && npm ci && npm run build
clean:
	rm -rf build/bin frontend/dist

.PHONY: package-deb
package-deb: build
	./scripts/package-deb.sh
