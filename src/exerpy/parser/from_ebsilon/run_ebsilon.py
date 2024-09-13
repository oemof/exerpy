"""
Ebsilon Model Processing Script

This script uses the EbsilonModelParser class to initialize, simulate, and parse an Ebsilon model,
then writes the extracted data to a JSON file. It handles paths, logging, and ensures output directories exist.
"""

import os
import logging
import ebsilon_parser  # Import the EbsilonModelParser class from ebsilon_parser module

# Configure logging to display info-level messages
logging.basicConfig(level=logging.INFO)

def run_ebsilon(path_ebs_file):
    """
    Main function to process the Ebsilon model and write data to a JSON file.
    """
    # Get the directory where the current script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to the Ebsilon model file (assumed to be in ../../simulations/ccpp.ebs)
    model_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'simulations', 'ccpp.ebs'))

    # Check if the model file exists at the specified path
    if not os.path.exists(model_path):
        logging.error(f"Model file not found at: {model_path}")
        return

    # Initialize the Ebsilon model parser with the model file path
    parser = ebsilon_parser.EbsilonModelParser(model_path)

    try:
        # Initialize the Ebsilon model within the parser
        parser.initialize_model()

        # Simulate the Ebsilon model
        parser.simulate_model()

        # Parse data from the simulated model
        parser.parse_model()
    except Exception as e:
        # Log any exceptions that occur during model processing
        logging.error(f"An error occurred during model processing: {e}")
        return

    # Define the output directory for the results (../results/results_from_ebsilon)
    output_dir = os.path.abspath(os.path.join(current_dir, '..', 'results', 'results_from_ebsilon'))
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define the output JSON file path
    output_file = os.path.join(output_dir, 'data_from_ebsilon.json')
    try:
        # Write the parsed data to the JSON file
        parser.write_to_json(output_file)
    except Exception as e:
        # Log any exceptions that occur during writing the output file
        logging.error(f"An error occurred while writing the output file: {e}")
        return

if __name__ == "__main__":
    # Run the main function when the script is executed
    main(path_ebs_file)
