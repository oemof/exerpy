import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.exerpy.parser.from_ebsilon import ebsilon_parser

model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ccpp.ebs'))
output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'results_ebsilon.json'))

ebsilon_parser.run_ebsilon(model_path, output_path)

