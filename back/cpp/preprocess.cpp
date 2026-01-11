#include <pybind11/pybind11.h>          //Allows exposing C++ functions to Python
#include <pybind11/numpy.h>             //Enables returing NumPy arrays from C++
#include <opencv2/opencv.hpp>           //Loads all OpenCV functionality 
 
using namespace std;
using namespace cv;
using namespace pybind11;


array_t<uint8_t> preprocess_image(string image_path){

    //step 1 : load the image
    Mat img= imread(image_path); // loads the image as a matrix (BGR format).
    if(img.empty()){
        throw runtime_error("Could not load image: " + image_path);
    }

    //step 2 : resize to recommended for CLIP => 224x224 also to achive consistency
    Mat resized;
    //resize(src, dst, Size(width, height))
    resize(img,resized,Size(224,224));

    // step 3 : denoising
    Mat denoised;
    /*
    fastNlMeansDenoisingColored(src, dst,
    hColor,       // strength for color noise
    hLuminance,   // strength for luminance noise
    templateWindowSize,
    searchWindowSize
    );
    */
    fastNlMeansDenoisingColored(resized,denoised,5,5,7,21); 

    //step 4 : Sharpening
    Mat blurred, sharpened;
    // GaussianBlur(src, dst, Size, sigmaX)
    GaussianBlur(denoised,blurred,Size(0,0),3);

    // addWeighted(src1, alpha, src2, beta, gamma, dst)
    addWeighted(denoised,1.5,blurred,-0.5, 0, sharpened);

    //step 5 : convert bgr -> rgb

    // cvtColor(src, dst, code)
    cvtColor(sharpened,sharpened,COLOR_BGR2RGB); //CLIP expects RGB

    //step 6 : convert c++ matrix -> Numpy Array
    return array_t<uint8_t> ({sharpened.rows, sharpened.cols, 3}, sharpened.data);
}

PYBIND11_MODULE(cpp_preprocess, m){
    m.def("preprocess_image", &preprocess_image, "Process image (resize,sharpen,denoise)");
}