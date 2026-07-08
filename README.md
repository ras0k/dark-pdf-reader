# Dark Mode Continuous PDF Reader

Does this already exist? Probably. 
Was it fun to make? Also yes.

A memory-optimized, flicker-free, continuous-scrolling PDF reader built with Python and Tkinter. 
This application automatically inverts document colors to provide a true high-contrast, white-on-black reading experience tailored for dark mode environments.

## Features

* **True Dark Mode:** Automatically inverts standard black-on-white text documents natively.
* **Continuous Scrolling:** Renders the document dynamically from top to bottom rather than utilizing static page breaks.
* **Flicker-Free Zoom:** Utilizes in-place image swapping to ensure smooth scaling without visual drops.
* **Memory Virtualization:** Implements lazy loading to exclusively render visible pages, preventing memory overflow on massive documents.
* **Drag and Drop:** Supports native OS file dropping directly into the viewport.

## Installation

Clone the repository and install the required dependencies:

```bash
git clone [https://github.com/yourusername/dark-pdf-reader.git](https://github.com/yourusername/dark-pdf-reader.git)
cd dark-pdf-reader
pip install -r requirements.txt
