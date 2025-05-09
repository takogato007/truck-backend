from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {
    "origins": [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://theloaddepot.com",
        "https://www.theloaddepot.com"
    ],
    "allow_headers": ["Content-Type"],
    "methods": ["POST", "OPTIONS"]
}})

@app.route('/api/optimize', methods=['POST', 'OPTIONS'])
def optimize():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json(force=True)
        app.logger.info('Received data: %s', data)

        if not data or 'truckSize' not in data or 'pallets' not in data:
            return jsonify({'errors': ['Invalid input data']}), 400

        truck_size = data.get('truckSize')
        pallets = data.get('pallets', [])

        truck_sizes = {
            '24ft': {'length': 316, 'width': 102, 'height': 108, 'max_weight': 20000},
            '40ft': {'length': 504, 'width': 102, 'height': 108, 'max_weight': 35000},
            '53ft': {'length': 640, 'width': 102, 'height': 108, 'max_weight': 45000}
        }

        if truck_size not in truck_sizes:
            return jsonify({'errors': ['Invalid truck size']}), 400

        truck = truck_sizes[truck_size]

        MAX_TOTAL_PALLETS = 60
        MAX_STACKABLE_PALLET_HEIGHT = 45
        MAX_STACK_HEIGHT = 90

        total_qty = len(pallets)
        if total_qty > MAX_TOTAL_PALLETS:
            return jsonify({'errors': [f'Total pallet quantity ({total_qty}) exceeds limit of {MAX_TOTAL_PALLETS}.']}), 400

        result_pallets = []
        pallet_counter = 1

        for pallet in pallets:
            try:
                length = float(pallet.get('length', 0))
                width = float(pallet.get('width', 0))
                height = float(pallet.get('height', 0))
                weight = float(pallet.get('weight', 0))
                stackable = bool(pallet.get('stackable', False))

                if stackable and height > MAX_STACKABLE_PALLET_HEIGHT:
                    return jsonify({
                        'errors': [
                            f'Stackable pallets must be ≤ {MAX_STACKABLE_PALLET_HEIGHT} inches tall. '
                            f'Total stacked height must not exceed {MAX_STACK_HEIGHT} inches.'
                        ]
                    }), 400

                if length <= 0 or width <= 0 or height <= 0 or weight <= 0:
                    return jsonify({'errors': ['Invalid pallet dimensions or weight']}), 400

                result_pallets.append({
                    'name': str(pallet_counter),
                    'length': length,
                    'width': width,
                    'height': height,
                    'weight': weight,
                    'stackable': stackable
                })
                pallet_counter += 1

            except (ValueError, TypeError) as e:
                return jsonify({'errors': [f'Invalid pallet data: {str(e)}']}), 400

        # === BEGIN POSITIONING LOGIC ===
        scale = 1
        spacing = 0
        x_cursor = 0
        y_cursor = 0
        row_height = 0
        placed_pallets = []

        stackables = [p for p in result_pallets if p['stackable']]
        non_stackables = [p for p in result_pallets if not p['stackable']]

        # Split stackables in half
        half = len(stackables) // 2
        bottom_stack = stackables[:half]
        top_stack = stackables[half:]

        # STEP 1: Place non-stackables first
        for pallet in non_stackables:
            if x_cursor + pallet['length'] > truck['length']:
                x_cursor = 0
                y_cursor += row_height + spacing
                row_height = 0

            pallet['x'] = x_cursor
            pallet['y'] = y_cursor
            placed_pallets.append(pallet)

            x_cursor += pallet['length'] + spacing
            row_height = max(row_height, pallet['width'])

        # Reset placement for bottom stacks
        x_cursor = 0
        y_cursor += row_height + spacing
        row_height = 0

        # STEP 2: Place bottom of stackables
        for bottom in bottom_stack:
            if x_cursor + bottom['length'] > truck['length']:
                x_cursor = 0
                y_cursor += row_height + spacing
                row_height = 0

            bottom['x'] = x_cursor
            bottom['y'] = y_cursor
            placed_pallets.append(bottom)

            x_cursor += bottom['length'] + spacing
            row_height = max(row_height, bottom['width'])

        # STEP 3: Stack top pallets directly on bottom ones
        for i, top in enumerate(top_stack):
            if i < len(bottom_stack):
                base = bottom_stack[i]
                top['x'] = base['x']
                top['y'] = base['y']  # Same position (frontend can offset vertically)
                placed_pallets.append(top)
            else:
                # If more tops than bottoms
                top['x'] = 0
                top['y'] = y_cursor + row_height + 20
                placed_pallets.append(top)

        # === END POSITIONING LOGIC ===

        return jsonify({
            'truck': truck,
            'pallets': placed_pallets
        }), 200

    except Exception as e:
        app.logger.error('Server error: %s', str(e))
        return jsonify({'errors': [f'Server error: {str(e)}']}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
