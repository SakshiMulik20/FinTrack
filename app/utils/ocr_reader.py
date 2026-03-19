import re
import numpy as np
from PIL import Image


def clean_amount(text):
    text = text.strip().replace(' ', '')
    if re.match(r'^\d{1,4},\d{2}$', text):
        return float(text.replace(',', '.'))
    cleaned = re.sub(r'[^\d.]', '', text)
    try:
        val = float(cleaned) if cleaned else None
        return val if val and val > 0 else None
    except:
        return None


def extract_amount_from_receipt(image_file):
    try:
        import easyocr
        image = Image.open(image_file).convert('RGB')
        img_array = np.array(image)

        reader = easyocr.Reader(['en'], verbose=False)
        results = reader.readtext(img_array)
        lines = [text for (_, text, conf) in results if conf > 0.3]
        full_text = ' | '.join(lines)
        print("EasyOCR detected lines:", lines)

        # Priority 1: Explicit Rs. / ₹ pattern — most reliable
        rs_pattern = re.compile(
            r'(?:rs\.?|₹|inr)\s*([1-9]\d{0,5}(?:[.,]\d{1,2})?)',
            re.IGNORECASE
        )
        rs_candidates = []
        for line in lines:
            matches = rs_pattern.findall(line)
            for m in matches:
                val = clean_amount(m)
                if val and 1 <= val <= 500000:
                    rs_candidates.append(val)
        if rs_candidates:
            best = max(rs_candidates)
            print(f"Rs. pattern found → {best}")
            return round(best, 2), full_text

        # Priority 2: Keyword + same/next line search
        def fuzzy_match(line, keywords):
            cleaned = line.lower().replace('|', 'l').replace('0', 'o').replace('aa', 'a')
            return any(kw in cleaned for kw in keywords)

        priority_keywords = [
            'grand total', 'net amount', 'total amount', 'net payable',
            'amount due', 'total due', 'net total', 'bill total',
            'gross total', 'round amount', 'payable', 'subtotal', 'total'
        ]

        for i, line in enumerate(lines):
            if fuzzy_match(line, priority_keywords):
                for j in range(i, min(i + 3, len(lines))):
                    nums = re.findall(r'[1-9][\d ,\.]+', lines[j])
                    for num in reversed(nums):
                        val = clean_amount(num)
                        if val and 1 <= val <= 500000:
                            print(f"Keyword '{line}' → {val}")
                            return round(val, 2), full_text

        # Priority 3: Fallback — prefer numbers WITH decimal point
        decimal_amounts = []
        integer_amounts = []
        for line in lines:
            nums = re.findall(r'[1-9][\d]*[.,]\d{2}', line)
            for num in nums:
                val = clean_amount(num)
                if val and 1 <= val <= 100000:
                    decimal_amounts.append(val)

            plain = re.findall(r'\b([1-9]\d{1,4})\b', line)
            for num in plain:
                val = clean_amount(num)
                if val and 1 <= val <= 10000:
                    integer_amounts.append(val)

        if decimal_amounts:
            best = max(decimal_amounts)
            print(f"Fallback (decimal): {best}")
            return round(best, 2), full_text

        if integer_amounts:
            best = max(integer_amounts)
            print(f"Fallback (integer): {best}")
            return round(best, 2), full_text

        return None, full_text

    except Exception as e:
        print(f"OCR error: {e}")
        return None, str(e)