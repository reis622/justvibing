from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

# Yerel çalışma için klasör yollarını netleştiriyoruz
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=current_dir, # HTML dosyasının olduğu yer
            static_folder=current_dir)   # Varsa resim/css klasörü için
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

@app.route('/')
def home():
    # Yerelde index.html dosyasını direkt sunar
    return render_template('index.html')

@app.route('/oneriler')
def oneriler():
    query = request.args.get('q')
    if not query: return jsonify([])
    search_url = f"https://www.transfermarkt.com.tr/schnellsuche/ergebnis/schnellsuche?query={query.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        if "profil" in res.url:
            h1 = soup.find('h1')
            return jsonify([{"id": res.url.split("transfermarkt.com.tr")[1], "name": h1.get_text(strip=True) if h1 else "Bilinmiyor", "photo": "", "club": "Direkt Sonuç"}])

        results = []
        table = soup.find('table', class_='items')
        if table:
            for row in table.find_all('tr', class_=['odd', 'even'])[:10]:
                link = row.find('td', class_='hauptlink').find('a')
                img = row.find('img')
                results.append({
                    "id": link['href'], 
                    "name": link.text.strip(), 
                    "photo": img['src'] if img else "", 
                    "club": "Futbolcu"
                })
        return jsonify(results)
    except Exception as e:
        return jsonify({"hata": str(e)})

@app.route('/detay')
def detay():
    path = request.args.get('path')
    url = f"https://www.transfermarkt.com.tr{path}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        details = {}
        info_elements = soup.find_all('span', class_='info-table__content--regular')
        for label in info_elements:
            key = label.get_text(strip=True).replace(":", "")
            val_span = label.find_next_sibling('span', class_='info-table__content--bold')
            if val_span:
                details[key] = val_span.get_text(" ", strip=True)

        market_val = "Veri Yok"
        val_div = soup.find('div', class_='tm-player-market-value-main__current-value')
        if val_div: 
            market_val = val_div.get_text(strip=True)
        else:
            forum_link = soup.find('a', href=re.compile(r"thread/forum"))
            if forum_link: market_val = forum_link.get_text(strip=True)

        photo_container = soup.find('div', class_='data-header__profile-container')
        photo_url = photo_container.find('img')['src'].replace("small", "header") if photo_container and photo_container.find('img') else ""

        achievements = []
        for box in soup.find_all('div', class_='data-header__success-data'):
            img = box.find('img')
            count = box.find('span', class_='data-header__success-number')
            if img and count: achievements.append({"title": img['title'], "count": count.text.strip()})

        # İsimdeki bitişikliği önlemek için boşlukla temizleme
        h1_title = soup.find('h1')
        isim_temiz = h1_title.get_text(" ", strip=True) if h1_title else "Bilinmiyor"

        return jsonify({
            "isim": isim_temiz,
            "tam_isim": details.get("Anavatandaki isim", "-"),
            "dogum": details.get("Doğum tarihi/Yaş", details.get("Doğum tarihi", "-")),
            "dogum_yeri": details.get("Doğum yeri", "-"),
            "boy": details.get("Boy", "-"),
            "uyruk": details.get("Uyruk", "-"),
            "mevki": details.get("Mevki", "-"),
            "ayak": details.get("Ayak", "-"),
            "takim": details.get("Güncel kulüp", "Kulüpsüz"),
            "sozlesme_bas": details.get("Sözleşme tarihi", "-"),
            "sozlesme_bit": details.get("Sözleşme sonu", "-"),
            "piyasa_degeri": market_val,
            "foto": photo_url,
            "achievements": achievements
        })
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

# YEREL ÇALIŞTIRMA AYARI
if __name__ == '__main__':
    # host='0.0.0.0' sayesinde aynı ağdaki iPhone'dan da erişebilirsin
    # debug=True sayesinde kodda hata yaparsan terminalde detayını görürsün
    app.run(host='0.0.0.0', port=5000, debug=True)