from flask import abort, redirect, request, send_from_directory, url_for

from ..database import get_connection
from ..services import documents as documents_service


def register(app):
    @app.route('/documents/<int:doc_id>/download')
    def download_document(doc_id):
        conn = get_connection()
        doc = documents_service.get_document(conn, doc_id)
        if not doc:
            abort(404)
        return send_from_directory(documents_service.DOCUMENTS_DIR, doc['relative_path'], as_attachment=True, download_name=doc['original_filename'])

    @app.route('/documents/<int:doc_id>/delete', methods=['POST'])
    def delete_document(doc_id):
        conn = get_connection()
        documents_service.delete_document(conn, doc_id)
        redirect_to = request.form.get('redirect_to') or ''
        if not redirect_to.startswith('/') or redirect_to.startswith('//'):
            redirect_to = url_for('list_parcels')
        return redirect(redirect_to)
