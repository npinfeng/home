from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import pandas as pd

app = FastAPI()

@app.get("/spider")
def spider(url: str):
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    results = []
    # 你可根据真实网页选择 class/id
    for item in soup.select(".paper"):
        title = item.select_one(".title").text.strip()
        author = item.select_one(".author").text.strip()
        chapter = item.select_one(".chapter").text.strip()

        results.append({
            "title": title,
            "author": author,
            "chapter": chapter
        })

    df = pd.DataFrame(results)
    df.to_excel("papers.xlsx", index=False)

    return {"status": "ok", "count": len(results), "data": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("paper_spider_api:app", host="0.0.0.0", port=8000)