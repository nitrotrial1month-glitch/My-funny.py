from flask import Blueprint, Response
from database import Database

sitemap_bp = Blueprint('sitemap_bp', __name__)

@sitemap_bp.route('/sitemap.xml')
def sitemap():
    products = Database.get_all_products()
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_content += '  <url><loc>https://my-funny-py.onrender.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
    
    for p in products:
        pid = p.get('WBM_P_ID', str(p.get('_id')))
        xml_content += f'  <url><loc>https://my-funny-py.onrender.com/product/{pid}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
    
    xml_content += '</urlset>'
    return Response(xml_content, mimetype='application/xml')
  
