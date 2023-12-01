#include "darknet.h"

#include <iostream>

int main() {
    image image_ = make_image(2, 3, 1);
    free_image(image_);
    return 0;
}
