# cpkg's first shape: two translation units, a header, a static archive.
CFLAGS ?= -O2 -Wall
all: hello
util.o: util.c util.h
	$(CC) $(CFLAGS) -c util.c -o util.o
hello.o: hello.c util.h
	$(CC) $(CFLAGS) -c hello.c -o hello.o
libutil.a: util.o
	$(AR) rcs libutil.a util.o
hello: hello.o libutil.a
	$(CC) $(CFLAGS) hello.o -L. -lutil -o hello
clean:
	rm -f hello hello.o util.o libutil.a
.PHONY: all clean
