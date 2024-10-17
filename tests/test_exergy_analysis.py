import pytest
import json
import os
from exerpy import ExergyAnalysis

@pytest.fixture
def exergy_analysis():
    """Set up the ExergyAnalysis object using the data from cgam_parsed.json."""
    # Define the path to the JSON file
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../examples/cgam_parsed.json'))
    
    # Load the JSON data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Extract components, connections, Tamb, and pamb
    components = data['components']
    connections = data['connections']
    Tamb = data['Tamb']
    pamb = data['pamb']
    
    # Return an initialized ExergyAnalysis object
    return ExergyAnalysis(components, connections, Tamb, pamb)

def test_exergy_analysis_results(exergy_analysis):
    """Test the overall exergy analysis results, allowing for a tolerance of 100."""
    fuel = {"inputs": ['1', '12'], "outputs": []}
    product = {"inputs": ['11', '9'], "outputs": ['8']}
    loss = {"inputs": ['7'], "outputs": []}
    exergy_analysis.analyse(fuel, product, loss)

    # Check the calculated values with a tolerance of 100
    assert pytest.approx(exergy_analysis.E_F, abs=100) == 84535746
    assert pytest.approx(exergy_analysis.E_P, abs=100) == 42754331
    assert pytest.approx(exergy_analysis.E_D, abs=100) == 39370528
    assert pytest.approx(exergy_analysis.E_L, abs=100) == 2410887
