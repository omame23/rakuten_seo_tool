import re
from django import template

register = template.Library()

@register.filter
def large_image(image_url, size="original"):
    """
    楽天画像URLのサイズパラメータを調整
    
    使用例:
    {{ item.product.image_url|large_image }}
    {{ item.product.image_url|large_image:"300x300" }}
    """
    if not image_url:
        return image_url
    
    # ?_ex=128x128のようなサイズパラメータを削除
    processed_url = re.sub(r'\?_ex=\d+x\d+', '', image_url)
    
    # &_ex=128x128のようなサイズパラメータも削除
    processed_url = re.sub(r'&_ex=\d+x\d+', '', processed_url)
    
    # 新しいサイズパラメータを追加（オプション）
    if size and size != "original":
        if '?' in processed_url:
            processed_url += f'&_ex={size}'
        else:
            processed_url += f'?_ex={size}'
    
    return processed_url