from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:5173", "http://localhost:3000", "https://theloaddepot.com"],
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
            app.logger.error('Invalid input data')
            return jsonify({'errors': ['Invalid input data']}), 400

        truck_size = data.get('truckSize')
        pallets = data.get('pallets', [])

        truck_sizes = {
            '24ft': {'length': 316, 'width': 102, 'height': 108, 'max_weight': 20000},
            '40ft': {'length': 504, 'width': 102, 'height': 108, 'max_weight': 35000},
            '53ft': {'length': 640, 'width': 102, 'height': 108, 'max_weight': 45000}
        }

        if truck_size not in truck_sizes:
            app.logger.error('Invalid truck size: %s', truck_size)
            return jsonify({'errors': ['Invalid truck size']}), 400

        truck = truck_sizes[truck_size]
        result_pallets = []

        total_qty = sum(pallet.get('qty', 1) for pallet in pallets)
        if total_qty > 20:
            app.logger.error('Total pallet quantity exceeds limit: %s', total_qty)
            return jsonify({'errors': [f'Total pallet quantity ({total_qty}) exceeds limit of 20.']}), 400

        pallet_counter = 1
        for pallet in pallets:
            try:
                qty = int(pallet.get('qty', 1))
                length = float(pallet.get('length', 0))
                width = float(pallet.get('width', 0))
                height = float(pallet.get('height', 0))
                weight = float(pallet.get('weight', 0))
                stackable = bool(pallet.get('stackable', False))

                app.logger.info('Processing pallet: qty=%s, length=%s, width=%s, height=%s, weight=%s, stackable=%s',
                                qty, length, width, height, weight, stackable)

                if qty <= 0:
                    app.logger.error('Invalid quantity: %s', qty)
                    return jsonify({'errors': ['Pallet quantity must be positive']}), 400
                if length <= 0 or width <= 0 or height <= 0 or weight <= 0:
                    app.logger.error('Invalid dimensions or weight: length=%s, width=%s, height=%s, weight=%s',
                                     length, width, height, weight)
                    return jsonify({'errors': ['Invalid pallet dimensions or weight']}), 400
                if stackable and height >= 50:
                    app.logger.error('Stackable pallets height under 50 inches: %s', height)
                    return jsonify({'errors': ['Stackable pallets must have height under 50 inches']}), 400

                for i in range(qty):
                    result_pallets.append({
                        'name': str(pallet_counter + i),
                        'length': length,
                        'width': width,
                        'height': height,
                        'weight': weight,
                        'stackable': stackable
                    })
                pallet_counter += qty

            except (ValueError, TypeError) as e:
                app.logger.error('Error processing pallet: %s', str(e))
                return jsonify({'errors': [f'Invalid pallet data: {str(e)}']}), 400

        app.logger.info('Processed %s pallets', len(result_pallets))
        return jsonify({
            'truck': truck,
            'pallets': result_pallets
        }), 200

    except Exception as e:
        app.logger.error('Server error: %s', str(e))
        return jsonify({'errors': [f'Server error: {str(e)}']}), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
