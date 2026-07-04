import json
import os
import sys

# Ensure backend module is available
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from app.main import app

def generate_docs():
    openapi = app.openapi()
    docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs', 'API.md'))
    
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write('# NetPulse API Documentation\n\n')
        f.write('This document is automatically generated from the OpenAPI schema.\n\n')
        
        for path, path_item in openapi.get('paths', {}).items():
            for method, operation in path_item.items():
                f.write(f'## {method.upper()} {path}\n')
                
                summary = operation.get('summary', '')
                if summary:
                    f.write(f'**Summary:** {summary}\n\n')
                    
                description = operation.get('description', '')
                if description:
                    f.write(f'{description}\n\n')
                    
                parameters = operation.get('parameters', [])
                if parameters:
                    f.write('### Parameters\n')
                    for param in parameters:
                        f.write(f"- `{param.get('name')}` ({param.get('in')}) - Required: {param.get('required', False)}\n")
                    f.write('\n')
                    
                responses = operation.get('responses', {})
                if responses:
                    f.write('### Responses\n')
                    for status, resp in responses.items():
                        desc = resp.get('description', '')
                        f.write(f"- `{status}`: {desc}\n")
                    f.write('\n')
                    
                f.write('---\n\n')

if __name__ == "__main__":
    generate_docs()
