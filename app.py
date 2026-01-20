from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

# Render için klasör yolları
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=current_dir, static_folder=current_dir)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

@app.route('/')
def home():
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
            return jsonify([{"id": res.url.split("transfermarkt.com.tr")[1], "name": h1.get_text(strip=True) if h1 else "Sonuç", "photo": "", "club": "Direkt Profil"}])

        results = []
        table = soup.find('table', class_='items')
        if table:
            for row in table.find_all('tr', class_=['odd', 'even'])[:10]:
                link_tag = row.find('td', class_='hauptlink')
                if link_tag and link_tag.find('a'):
                    link = link_tag.find('a')
                    img = row.find('img')
                    results.append({
                        "id": link['href'],
                        "name": link.text.strip(),
                        "photo": img['src'] if img else "",
                        "club": "Futbolcu"
                    })
        return jsonify(results)
    except Exception as e:
        return jsonify([])

@app.route('/detay')
def detay():
    path = request.args.get('path')
    url = f"https://www.transfermarkt.com.tr{path}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Piyasa Değeri: Spandan önceki saf metni çekiyoruz (Örn: 12.00)
        market_val = "Veri Yok"
        mv_wrapper = soup.find('a', class_='data-header__market-value-wrapper')
        if mv_wrapper:
            val_text = mv_wrapper.find(text=True, recursive=False)
            waehrung = mv_wrapper.find('span', class_='waehrung')
            if val_text:
                market_val = val_text.strip()
                if waehrung:
                    market_val += " " + waehrung.get_text(strip=True)

        details = {}
        info_elements = soup.find_all('span', class_='info-table__content--regular')
        for label in info_elements:
            key = label.get_text(strip=True).replace(":", "")
            val_span = label.find_next_sibling('span', class_='info-table__content--bold')
            if val_span:
                details[key] = val_span.get_text(" ", strip=True)

        photo_container = soup.find('div', class_='data-header__profile-container')
        photo_url = photo_container.find('img')['src'].replace("small", "header") if photo_container and photo_container.find('img') else ""

        achievements = []
        for box in soup.find_all('div', class_='data-header__success-data'):
            img = box.find('img')
            count = box.find('span', class_='data-header__success-number')
            if img and count: achievements.append({"title": img['title'], "count": count.text.strip()})

        h1_title = soup.find('h1')
        isim_temiz = h1_title.get_text(" ", strip=True) if h1_title else "Bilinmiyor"

        return jsonify({
            "isim": isim_temiz,
            "tam_isim": details.get("Anavatandaki isim", "-"),
            "dogum": details.get("Doğum tarihi/Yaş", "-"),
            "takim": details.get("Güncel kulüp", "Kulüpsüz"),
            "mevki": details.get("Mevki", "-"),
            "boy": details.get("Boy", "-"),
            "uyruk": details.get("Uyruk", "-"),
            "ayak": details.get("Ayak", "-"),
            "sozlesme_bit": details.get("Sözleşme sonu", "-"),
            "piyasa_degeri": market_val,
            "foto": photo_url,
            "achievements": achievements
        })
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)