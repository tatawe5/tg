import re
import logging
from typing import List, Tuple
from word2number import w2n

logger = logging.getLogger(__name__)

class NumberExtractor:
    def __init__(self):
        # Word-to-number mapping including common variations
        self.word_to_number = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'oh': '0', 'o': '0',  # Common ways to say zero
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90', 'hundred': '100', 'thousand': '1000'
        }
        
        # Common filler words to ignore
        self.filler_words = {
            'um', 'uh', 'er', 'ah', 'like', 'you', 'know', 'well', 'so',
            'and', 'the', 'is', 'it', 'my', 'its', 'that', 'this', 'yes',
            'okay', 'alright', 'sure', 'hello', 'hi', 'speaking'
        }
        
        # Context keywords that often precede numbers
        self.context_keywords = [
            'pin', 'password', 'code', 'number', 'id', 'verification',
            'security', 'access', 'account', 'phone', 'social', 'zip',
            'postal', 'credit', 'card', 'ssn', 'license', 'passport'
        ]
    
    def extract_numbers_from_speech(self, transcription: str) -> Tuple[List[str], float]:
        """
        Extract numbers from speech transcription using multiple methods
        Returns: (list of extracted numbers, confidence score)
        """
        if not transcription:
            return [], 0.0
        
        logger.info(f"Processing transcription: {transcription}")
        
        # Clean and normalize text
        text = self._clean_text(transcription)
        
        # Try multiple extraction methods
        extracted_numbers = []
        confidence_scores = []
        
        # Method 1: Direct digit extraction
        direct_digits = self._extract_direct_digits(text)
        if direct_digits:
            extracted_numbers.extend(direct_digits)
            confidence_scores.append(0.9)
        
        # Method 2: Word-to-number conversion
        word_numbers = self._extract_word_numbers(text)
        if word_numbers:
            extracted_numbers.extend(word_numbers)
            confidence_scores.append(0.8)
        
        # Method 3: Context-aware extraction
        context_numbers = self._extract_context_numbers(text)
        if context_numbers:
            extracted_numbers.extend(context_numbers)
            confidence_scores.append(0.85)
        
        # Method 4: Sequential number detection
        sequential_numbers = self._extract_sequential_numbers(text)
        if sequential_numbers:
            extracted_numbers.extend(sequential_numbers)
            confidence_scores.append(0.75)
        
        # Method 5: Advanced pattern matching
        pattern_numbers = self._extract_pattern_numbers(text)
        if pattern_numbers:
            extracted_numbers.extend(pattern_numbers)
            confidence_scores.append(0.7)
        
        # Remove duplicates and filter by length
        unique_numbers = self._filter_and_dedupe(extracted_numbers)
        
        # Calculate overall confidence
        overall_confidence = max(confidence_scores) if confidence_scores else 0.0
        
        logger.info(f"Extracted numbers: {unique_numbers} (confidence: {overall_confidence:.2f})")
        
        return unique_numbers, overall_confidence
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for processing"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation except dashes and spaces
        text = re.sub(r'[^\w\s\-]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_direct_digits(self, text: str) -> List[str]:
        """Extract sequences of digits directly"""
        # Enhanced patterns for better 8-digit and longer number detection
        digit_patterns = [
            r'\b(\d{3,})\b',  # Basic digit sequences (3+ digits)
            r'\b(\d{8})\b',   # Specifically target 8-digit sequences
            r'\b(\d{4}\s*\d{4})\b',  # 8-digit with optional space in middle
            r'(\d{1,4}[-\s]\d{1,4}[-\s]\d{1,4})',  # Separated sequences
            r'(\d{1,3}\s+\d{1,3}\s+\d{1,3}\s+\d{1,3})',  # 4-part space-separated
            r'(\d{2}\s+\d{2}\s+\d{2}\s+\d{2})',  # 8-digit as 4 pairs
            r'(\d{1}\s+\d{1}\s+\d{1}\s+\d{1}\s+\d{1}\s+\d{1}\s+\d{1}\s+\d{1})',  # 8 individual digits
        ]
        
        extracted = []
        for pattern in digit_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Clean the match and extract only digits
                digits = re.sub(r'[^\d]', '', match)
                if len(digits) >= 3:  # Accept 3+ digit sequences
                    extracted.append(digits)
        
        return extracted
    
    def _extract_word_numbers(self, text: str) -> List[str]:
        """Convert spoken numbers to digits"""
        extracted = []
        
        # Split text into words
        words = text.split()
        
        # Find sequences of number words
        number_sequences = []
        current_sequence = []
        
        for word in words:
            if word in self.word_to_number or word.isdigit():
                current_sequence.append(word)
            elif word not in self.filler_words and current_sequence:
                if len(current_sequence) >= 2:  # At least 2 number words
                    number_sequences.append(current_sequence)
                current_sequence = []
            # Continue sequence if it's a filler word
        
        # Don't forget the last sequence
        if len(current_sequence) >= 2:
            number_sequences.append(current_sequence)
        
        # Convert each sequence to digits
        for sequence in number_sequences:
            digits = self._convert_word_sequence_to_digits(sequence)
            if digits and len(digits) >= 3:
                extracted.append(digits)
        
        return extracted
    
    def _convert_word_sequence_to_digits(self, word_sequence: List[str]) -> str:
        """Convert a sequence of number words to digits"""
        digits = ""
        
        for word in word_sequence:
            if word.isdigit():
                digits += word
            elif word in self.word_to_number:
                digit = self.word_to_number[word]
                # Handle special cases like "hundred", "thousand"
                if word in ['hundred', 'thousand']:
                    # These modify the previous number
                    continue
                digits += digit
        
        return digits
    
    def _extract_context_numbers(self, text: str) -> List[str]:
        """Extract numbers that appear after context keywords"""
        extracted = []
        
        for keyword in self.context_keywords:
            # Look for patterns like "pin is 1234" or "code: one two three four"
            patterns = [
                rf'{keyword}\s+(?:is|number|code)?\s*(\d{{3,}})',
                rf'{keyword}\s+(?:is|number|code)?\s*([zero-nine\s]{{10,}})',
                rf'my\s+{keyword}\s+(?:is|number)?\s*(\d{{3,}})',
                rf'the\s+{keyword}\s+(?:is|number)?\s*(\d{{3,}})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match.isdigit():
                        extracted.append(match)
                    else:
                        # Convert word numbers
                        digits = self._convert_words_to_digits(match)
                        if digits and len(digits) >= 3:
                            extracted.append(digits)
        
        return extracted
    
    def _extract_sequential_numbers(self, text: str) -> List[str]:
        """Extract sequences of individual numbers spoken one by one"""
        # Pattern for sequences like "one two three four five six"
        words = text.split()
        sequences = []
        current_sequence = []
        
        for word in words:
            if word in self.word_to_number and word not in ['hundred', 'thousand']:
                current_sequence.append(self.word_to_number[word])
            elif word.isdigit() and len(word) == 1:
                current_sequence.append(word)
            elif word not in self.filler_words:
                if len(current_sequence) >= 3:
                    sequences.append(''.join(current_sequence))
                current_sequence = []
        
        # Don't forget the last sequence
        if len(current_sequence) >= 3:
            sequences.append(''.join(current_sequence))
        
        return sequences
    
    def _extract_pattern_numbers(self, text: str) -> List[str]:
        """Extract numbers using advanced pattern matching"""
        patterns = [
            r'(?:call|phone|dial)\s+(\d{10,})',  # Phone numbers
            r'(?:zip|postal)\s+(?:code)?\s*(\d{5})',  # ZIP codes
            r'(?:ssn|social)\s+(?:security)?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{4})',  # SSN
            r'(\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4})',  # Credit card
            r'(?:account|member)\s+(?:number)?\s*(\d{6,})',  # Account numbers
        ]
        
        extracted = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                digits = re.sub(r'[^\d]', '', match)
                if len(digits) >= 3:
                    extracted.append(digits)
        
        return extracted
    
    def _convert_words_to_digits(self, text: str) -> str:
        """Convert a string containing number words to digits"""
        digits = ""
        words = text.split()
        
        for word in words:
            if word in self.word_to_number:
                digits += self.word_to_number[word]
            elif word.isdigit():
                digits += word
        
        return digits
    
    def _filter_and_dedupe(self, numbers: List[str]) -> List[str]:
        """Filter numbers by length and remove duplicates"""
        # Remove duplicates while preserving order
        seen = set()
        unique_numbers = []
        
        for num in numbers:
            # Accept any sequence of 3+ digits, including 8-digit numbers
            if num not in seen and len(num) >= 3 and len(num) <= 20:  # Up to 20 digits max
                seen.add(num)
                unique_numbers.append(num)
        
        # Sort by length (longer numbers first) then by value
        # This ensures 8-digit numbers appear before shorter ones
        unique_numbers.sort(key=lambda x: (-len(x), x))
        
        return unique_numbers
    
    def extract_with_advanced_nlp(self, text: str) -> List[str]:
        """Advanced extraction using word2number library"""
        try:
            # Try to extract using word2number for more complex number expressions
            words = text.split()
            extracted = []
            
            # Look for number word sequences
            for i in range(len(words)):
                for j in range(i + 2, min(i + 10, len(words) + 1)):  # Max 10 words
                    phrase = ' '.join(words[i:j])
                    try:
                        number = w2n.word_to_num(phrase)
                        if number and len(str(number)) >= 3:
                            extracted.append(str(number))
                    except:
                        continue
            
            return extracted
        except Exception as e:
            logger.warning(f"Advanced NLP extraction failed: {e}")
            return []
