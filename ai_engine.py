"""
AI Contract Generator with Multi-Layer Validation
Compliance: EU AI Act Tier 2, IEEE EAD
"""

import openai
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Tuple

load_dotenv()
openai.api_key = os.getenv('PERPLEXITY_API_KEY')

# Configure structured logging
logging.basicConfig(
    filename='ai_generations.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)


class ContractGenerator:
    """Deterministic PyTeal code generator with self-correction loop."""
    
    SYSTEM_PROMPT = """You are an expert Algorand blockchain developer specialized in PyTeal smart contracts.

    *CRITICAL REQUIREMENTS:*
    1. Generate ONLY valid PyTeal code compatible with pyteal v0.24.0
    2. Use proper approval/clear program structure
    3. Include comprehensive inline comments
    4. Follow Algorand ASC1 security standards
    5. Avoid:
    - Hardcoded addresses or keys
    - Unbounded loops
    - Reentrancy vulnerabilities
    - Unsafe global state manipulation
    - Integer overflow risks
    6. Always include proper fee checks and transaction validation
    7. Use defensive programming patterns

    *OUTPUT STRUCTURE:*
    1. Complete PyTeal source code
    2. Contract purpose summary (2-3 sentences)
    3. Logic walkthrough (key conditions and branches)
    4. Security considerations
    5. Deployment parameters needed"""

    def _init_(self, model: str = "gpt-4", temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        self.generation_history = []
    
    def generate_pyteal_contract(
        self, 
        description: str, 
        max_retries: int = 3
    ) -> Dict[str, str]:
        """
        Generate PyTeal contract with automatic validation and retry.
        
        Returns:
            Dict with keys: code, explanation, deployment, audit
        """
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                logging.info(f"Generation attempt {attempt + 1} for: {description[:100]}")
                
                # Initial generation
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": self._build_user_prompt(description, last_error)}
                    ],
                    temperature=self.temperature,
                    max_tokens=2000
                )
                
                raw_output = response['choices'][0]['message']['content']
                parsed = self._parse_ai_response(raw_output)
                
                # Syntax pre-validation
                validation_result = self._validate_pyteal_syntax(parsed['code'])
                
                if validation_result['valid']:
                    # Log successful generation
                    self._log_generation(description, parsed, attempt + 1)
                    return {
                        'success': True,
                        'code': parsed['code'],
                        'explanation': parsed['explanation'],
                        'deployment': parsed['deployment'],
                        'audit': parsed['audit'],
                        'metadata': {
                            'model': self.model,
                            'attempts': attempt + 1,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    }
                else:
                    last_error = validation_result['error']
                    attempt += 1
                    logging.warning(f"Validation failed: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                attempt += 1
                logging.error(f"Generation error: {e}")
        
        # All retries exhausted
        return {
            'success': False,
            'error': f"Failed after {max_retries} attempts. Last error: {last_error}",
            'partial_code': None
        }
    
    def _build_user_prompt(self, description: str, previous_error: str = None) -> str:
        """Construct user prompt with self-correction context."""
        base = f"""Generate a PyTeal smart contract for the following requirement:

        {description}

        Ensure the contract is production-ready and follows all security guidelines."""
                
        if previous_error:
                    base += f"""

        PREVIOUS ATTEMPT FAILED WITH ERROR:
        {previous_error}

        Please regenerate with corrections addressing the above error. Focus on:
        - Proper PyTeal syntax and imports
        - Correct transaction field validation
        - Safe state management"""
        
        return base
    
    def _parse_ai_response(self, raw_text: str) -> Dict[str, str]:
        """Extract structured sections from AI response."""
        sections = {
            'code': '',
            'explanation': '',
            'deployment': '',
            'audit': ''
        }
        
        # Extract code block
        if '```' in raw_text:
            code_start = raw_text.find('python') + 9
            code_end = raw_text.find('```', code_start)
            if code_end == -1:  # Fallback if no closing ``` found
                sections['code'] = raw_text[code_start:code_end].strip()
        elif '' in raw_text:
            code_start = raw_text.find('```')
            code_end = raw_text.find('', code_start)
            sections['code'] = raw_text[code_start:code_end].strip()
        
        # Extract other sections (simple heuristic)
        lines = raw_text.split('\n')
        current_section = None
        
        for line in lines:
            lower = line.lower()
            if 'explanation' in lower or 'purpose' in lower:
                current_section = 'explanation'
            elif 'deployment' in lower or 'deploy' in lower:
                current_section = 'deployment'
            elif 'audit' in lower or 'security' in lower or 'vulnerab' in lower:
                current_section = 'audit'
            elif current_section and line.strip():
                sections[current_section] += line + '\n'
        
        return sections
    
    def _validate_pyteal_syntax(self, code: str) -> Dict[str, any]:
        """
        Basic PyTeal syntax validation without execution.
        More robust validation happens in algorand_utils.py
        """
        try:
            # Check for required imports
            required_imports = ['from pyteal import', 'import pyteal']
            has_import = any(imp in code for imp in required_imports)
            
            if not has_import:
                return {'valid': False, 'error': 'Missing PyTeal import statement'}
            
            # Check for approval program structure
            required_keywords = ['Approve', 'Reject', 'Return']
            has_logic = any(kw in code for kw in required_keywords)
            
            if not has_logic:
                return {'valid': False, 'error': 'No approval/rejection logic found'}
            
            # Check for dangerous patterns
            dangerous = ['eval(', 'exec(', '_import_']
            if any(d in code for d in dangerous):
                return {'valid': False, 'error': 'Dangerous code pattern detected'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def _log_generation(self, description: str, parsed: Dict, attempts: int):
        """Log generation for audit trail."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'description': description[:200],
            'attempts': attempts,
            'code_length': len(parsed['code']),
            'model': self.model
        }
        self.generation_history.append(log_entry)
        logging.info(f"Successful generation: {json.dumps(log_entry)}")


def explain_contract(code: str) -> str:
    """
    Use GPT-4 to provide human-readable explanation of existing PyTeal code.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at explaining blockchain smart contracts in simple terms. "
                               "Provide a clear, non-technical summary suitable for business stakeholders."
                },
                {
                    "role": "user",
                    "content": f"Explain this PyTeal smart contract:\n\n{code}\n\n"
                               f"Include: purpose, key operations, user interactions, and risks."
                }
            ],
            temperature=0.3,
            max_tokens=800
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        logging.error(f"Explanation generation failed: {e}")
        return f"Error generating explanation: {str(e)}"