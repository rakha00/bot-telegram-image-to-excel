"""
Modul bantuan untuk menyediakan fungsi-fungsi pendukung.
"""

def ensure_safe_html_for_pre(text: str) -> str:
    """
    Memastikan bahwa teks aman untuk dikirim sebagai HTML di Telegram,
    terutama dengan mengganti karakter sensitif dan memastikan tag <pre> seimbang.
    """
    # Ganti karakter HTML sensitif untuk mencegah injeksi atau kesalahan parsing.
    safe_text = text.replace('<', '<').replace('>', '>')
    
    # Logika sederhana untuk memastikan tag <pre> selalu ditutup untuk pembaruan streaming.
    # Ini adalah pendekatan yang lebih sederhana yang cocok untuk kasus penggunaan kita.
    if safe_text.count('<pre>') > safe_text.count('</pre>'):
        safe_text += '</pre>'
        
    return safe_text