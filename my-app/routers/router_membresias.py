from flask import Blueprint, redirect, url_for
from routers.router_login import requiere_permiso

membresias_bp = Blueprint('membresias', __name__)


@membresias_bp.get('/membresias')
@requiere_permiso('socios.ver')
def lista():
    return redirect(url_for('socios.lista', tab='pagos'))
