import streamlit as st
import time

class OrionUI:
    def __init__(self):
        self.input_file = None
        self.output_file = None
        self.seq_filename = None
        self.results_heatmap_ortho = None
        self.results_heatmap_path = None
        self.results_plots = None
        self.json_legacy_output = None
        self.results_report = None
        self.results_excel_file = None

    # Function to show the image
    def show_image(self):
        st.image("layout.png", caption="Layout Image")

    # Inject CSS to change font color
    st.markdown(
        """
        <style>
        body, .stButton button, .stTextInput, .stFileUploader label {
            color: black !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Function to show the new page with specific layout
    def show_new_page(self):
        st.title("Origami Design Optimizer")

        # File uploader for JSON
        self.input_file = st.file_uploader(
            "", type=["json"]
        )

        # Input for file path to save the result
        self.output_file = st.text_input("Select a file path to save the final result")

        # Initialize the 'running' state if it doesn't exist
        if "running" not in st.session_state:
            st.session_state.running = False

        # Check if both file and path are provided to enable the 'Run' button
        if self.input_file and self.output_file:
            # Activate Run button
            if st.button("Run", disabled=st.session_state.running):
                st.session_state.running = True
                st.rerun()

            if st.session_state.running:
                st.write("Running the optimization process...")
                
                # TODO:
                    # Can you even run a Bayesian optimizatin process in a streamlit app?
                    
                # TODO:
                # Modify the method parse_args_from_shell() to take in the command line arguments as parameters instead
                # of reading from the command line, since we are using streamlit
                # Then modify the autobreak_main.py to return the Gibbs Free Energy value,
                # and save the final result to the provided file path

                time.sleep(5)  # Simulating a 5-second process

                st.success("Process completed!")
                st.session_state.running = False
        # else:
        #     # Display messages when either file or path is missing
        #     if not self.input_file:
        #         st.warning("Please upload a JSON file.")
        #     if not self.output_file:
        #         st.warning("Please provide a file path.")

    # Initialize session state
    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()
        st.session_state.show_image = True


# Main app logic
def main():
    stream = OrionUI()
    show_image = stream.show_image
    if st.session_state.show_image:
        show_image()
        # Check if 3 seconds have passed
        if time.time() - st.session_state.start_time > 3:
            st.session_state.show_image = False
            st.rerun()
    else:
        stream.show_new_page()

    # Force a rerun every 0.1 seconds while showing the image
    if st.session_state.show_image:
        time.sleep(0.1)
        st.rerun()


if __name__ == "__main__":
    main()
