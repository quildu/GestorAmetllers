import csv
import io

from flask import make_response, render_template

from ..database import get_connection
from ..services import reports as reports_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/reports')
    def reports(parcel_id):
        conn = get_connection()
        expenses_by_type = reports_service.expenses_by_type(conn, parcel_id)
        return render_template('reports.html', expenses_by_type=expenses_by_type)

    @app.route('/parcela/<int:parcel_id>/export/csv/<string:category>')
    def export_csv(parcel_id, category):
        conn = get_connection()
        export = reports_service.get_export_data(conn, parcel_id, category)
        if export is None:
            return "Invalid"
        header, rows = export

        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(header)
        for row in rows:
            cw.writerow(list(row))

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={category}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
