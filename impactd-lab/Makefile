CC = cc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -O0 -g

.PHONY: test demo sanitize clean doctor check coverage
doctor:
	CC="$(CC)" python3 scripts/check.py --doctor
check:
	CC="$(CC)" python3 scripts/check.py
coverage:
	python3 scripts/coverage.py collect
build/test_image: fixture/image.c fixture/image.h fixture/test_image.c
	mkdir -p build
	$(CC) $(CFLAGS) fixture/image.c fixture/test_image.c -o $@
test: build/test_image
	./build/test_image
demo:
	CC="$(CC)" python3 scripts/demo.py
sanitize:
	mkdir -p build
	$(CC) $(CFLAGS) -fsanitize=address,undefined -fno-omit-frame-pointer fixture/image.c fixture/test_image.c -o build/test_image_sanitized
	./build/test_image_sanitized
clean:
	rm -rf build
