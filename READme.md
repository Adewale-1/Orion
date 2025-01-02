The codebase provided is part of a larger application designed for DNA origami design optimization. The application is  structured into a main GUI component (`main.py`) and a backend processing component (`autobreak_main.py`), along with other supporting modules like `exportoligos.py`. Here's an overview of how to run the application and the role of each file:

### Running the Application

1. **Starting the Application**: The entry point of the application is `main.py`. This script initializes a GUI where the user can upload an input file and select an output directory.

2. **Input and Output**: The user selects a JSON input file and an output directory through the GUI. The 'Run' button becomes active after these selections are made.

3. **Optimization Prompt**: Upon starting the optimization process, the user is prompted to confirm if they wish to proceed. If confirmed, the optimization begins.

4. **Ending Optimization**: The user has the option to end the optimization process prematurely if desired.

5. **Results**: Once the optimization is complete, the results are saved to the initially specified download path.

6. **Result Information**: A tooltip in the top right corner of the GUI provides information about the results.

### File Descriptions

- **`main.py`**: This is the main GUI application file. It handles user interactions, file uploads, and initiates the optimization process. It also displays results and provides a tooltip for additional information about the output.

  - Relevant code block: `startLine: 212, endLine: 1129`

- **`autobreak_main.py`**: This file contains the core logic for the optimization process. It defines the `AutoBreak` class, which includes methods for setting up the optimization parameters, running the optimization, and handling the results.

  - Relevant code block: `startLine: 602, endLine: 3000`

- **`exportoligos.py`**: This script seems to be related to the processing of oligonucleotides, possibly for exporting them in a specific format or for use with lab equipment like the ECHO liquid handler.
  - Relevant code block: `startLine: 1862, endLine: 2110`

### Additional Notes

- **Estimation of Run Time**: The code includes a mechanism to estimate the time required to run the optimization. However, it is noted that the current estimation is not accurate and should be ignored.
- **Optimization Process**: The optimization process is likely computationally intensive and may take a significant amount of time, during which the user has the option to terminate the process.
- **Results Handling**: After the optimization, the results are compiled, and a summary is provided to the user. The results include detailed information about the optimized DNA origami design.
