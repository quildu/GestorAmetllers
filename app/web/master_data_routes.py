from flask import jsonify, request

from ..database import get_connection
from ..services import catalog as catalog_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/master/worker/add', methods=['POST'])
    def quick_add_worker(parcel_id):
        name = request.form.get('name')
        if name:
            conn = get_connection()
            try:
                new_id = catalog_service.quick_add_worker(conn, parcel_id, name)
                return jsonify({'success': True, 'id': new_id, 'name': name})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        return jsonify({'success': False, 'error': 'Nom buit'}), 400

    @app.route('/parcela/<int:parcel_id>/master/labor_type/add', methods=['POST'])
    def quick_add_labor_type(parcel_id):
        name = request.form.get('name')
        if name:
            conn = get_connection()
            try:
                new_id = catalog_service.quick_add_labor_type(conn, parcel_id, name)
                return jsonify({'success': True, 'id': new_id, 'name': name})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        return jsonify({'success': False, 'error': 'Nom buit'}), 400

    @app.route('/parcela/<int:parcel_id>/master/expense_type/add', methods=['POST'])
    def quick_add_expense_type(parcel_id):
        name = request.form.get('name')
        if name:
            conn = get_connection()
            try:
                new_id = catalog_service.quick_add_expense_type(conn, parcel_id, name)
                return jsonify({'success': True, 'id': new_id, 'name': name})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400
        return jsonify({'success': False, 'error': 'Nom buit'}), 400
