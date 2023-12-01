#include <stdio.h>
#include <pulse/pulseaudio.h>

int main()
{
    printf("pulse audio versions %s\n", pa_get_library_version());
    return 0;
}
