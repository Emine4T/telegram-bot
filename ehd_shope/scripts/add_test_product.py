import json

try:
    from ehd_shope.services.inventory_service import InventoryService
except ImportError:
    from services.inventory_service import InventoryService

p = {
    "category": "electronics",
    "image_url": "https://via.placeholder.com/600x400.png?text=Test+Product",
    "name": "Test Phone",
    "description": "A test product added by assistant.",
    "price": 1999,
    "stock": 5,
    "details": "Color: black, material: cotton",
    "is_active": True,
}
svc = InventoryService()
added = svc.add_product(p)
print('INSERTED:', json.dumps({'_id': str(added.get('_id')), 'name': added.get('name')}, ensure_ascii=False))
prods = svc.list_products()
out=[{'_id':str(x.get('_id')),'name':x.get('name'),'price':x.get('price'),'stock':x.get('stock'),'has_image':bool(x.get('image_file_id') or x.get('image_url')),'image_file_id':x.get('image_file_id'),'image_url':x.get('image_url'),'description':x.get('description')} for x in prods]
print(json.dumps(out, ensure_ascii=False, indent=2))
