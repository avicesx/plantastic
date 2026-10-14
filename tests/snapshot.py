"""
берёт все фотографии из tests/images/, отправляет каждую в backend и либо сохраняет ответы как
эталон, либо сравнивает с ранее сохранённым эталоном

1. фото в tests/images/ (растения, больные листья, не-растения)
2. запустить СТАРУЮ версию и снять эталон:
python tests/snapshot.py record
3. после переключения на новый сервис сравнить:
python tests/snapshot.py check
"""


from __future__ import annotations
import argparse
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
ENDPOINTS = ("identify_plant", "identify_disease")

# допустимое расхождение уверенности
CONFIDENCE_TOLERANCE = 0.05


def post_image(url: str, path: Path, timeout: float, retries: int = 8) -> tuple[dict, float]:
    """Отправляет файл multipart-запросом. Возвращает (ответ, время в секундах)"""
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    for attempt in range(retries):
        boundary = uuid.uuid4().hex
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8")
        body = head + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                elapsed = time.perf_counter() - started
                return json.loads(response.read().decode("utf-8")), elapsed
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < retries - 1:
                print("    (лимит запросов, жду 10 с...)", flush=True)
                time.sleep(10)
                continue
            detail = error.read().decode("utf-8", errors="replace")[:200]
            return {"http_error": error.code, "detail": detail}, time.perf_counter() - started
        except (urllib.error.URLError, TimeoutError) as error:
            return {"http_error": 0, "detail": str(error)}, time.perf_counter() - started
    return {"http_error": 429, "detail": "rate limit"}, 0.0


def normalize(response: dict) -> dict:
    """Оставляет в ответе только то, что должно совпадать (без времени и ссылок на картинки)"""
    if "http_error" in response:
        return {"http_error": response["http_error"]}
    return {
        "status": response.get("status"),
        "total": response.get("total"),
        "data": [
            {
                "item_id": item.get("item_id"),
                "item_name": item.get("item_name"),
                "confidence": item.get("confidence"),
            }
            for item in response.get("data", [])
        ],
    }


def collect_images(images_dir: Path) -> list[Path]:
    return sorted(
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def run(base_url: str, images: list[Path], timeout: float) -> tuple[dict, dict[str, list[float]]]:
    results: dict[str, dict] = {}
    timings: dict[str, list[float]] = {name: [] for name in ENDPOINTS}
    for index, image in enumerate(images, 1):
        print(f"[{index}/{len(images)}] {image.name}", flush=True)
        results[image.name] = {}
        for endpoint in ENDPOINTS:
            response, elapsed = post_image(f"{base_url}/{endpoint}", image, timeout)
            normalized = normalize(response)
            results[image.name][endpoint] = normalized
            timings[endpoint].append(elapsed)
            print(f"    {endpoint:17s} {elapsed:6.2f} с  {describe(normalized)}", flush=True)
    return results, timings


def describe(normalized: dict) -> str:
    if "http_error" in normalized:
        return f"ОШИБКА HTTP {normalized['http_error']}"
    if normalized["status"] != "ok":
        return normalized["status"]
    top = normalized["data"][0] if normalized["data"] else None
    return f"{top['item_name']} ({top['confidence']}%)" if top else "пусто"


def compare(expected: dict, actual: dict) -> list[str]:
    """Возвращает список расхождений (пустой, если ответы совпали)"""
    problems: list[str] = []
    for image_name, endpoints in expected.items():
        for endpoint, exp in endpoints.items():
            act = actual.get(image_name, {}).get(endpoint)
            where = f"{image_name} / {endpoint}"
            if act is None:
                problems.append(f"{where}: нет ответа")
                continue
            if "http_error" in exp or "http_error" in act:
                if exp != act:
                    problems.append(f"{where}: было {exp}, стало {act}")
                continue
            if exp["status"] != act["status"]:
                problems.append(f"{where}: статус был {exp['status']!r}, стал {act['status']!r}")
                continue
            exp_items, act_items = exp["data"], act["data"]
            if [i["item_id"] for i in exp_items] != [i["item_id"] for i in act_items] or \
               [i["item_name"] for i in exp_items] != [i["item_name"] for i in act_items]:
                problems.append(
                    f"{where}: другой набор/порядок предсказаний\n"
                    f"      было:  {[i['item_name'] for i in exp_items]}\n"
                    f"      стало: {[i['item_name'] for i in act_items]}"
                )
                continue
            for e, a in zip(exp_items, act_items):
                if abs(e["confidence"] - a["confidence"]) > CONFIDENCE_TOLERANCE:
                    problems.append(
                        f"{where}: уверенность для {e['item_name']}: было {e['confidence']}, стало {a['confidence']}"
                    )
    return problems


def print_timings(timings: dict[str, list[float]]) -> None:
    print("\nСреднее время ответа:")
    for endpoint, values in timings.items():
        if values:
            print(f"  {endpoint:17s} {sum(values) / len(values):6.2f} с  (запросов: {len(values)})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("record", "check"), help="record - сохранить эталон, check - сравнить с эталоном")
    parser.add_argument("--url", default="http://localhost:8000", help="адрес backend (по умолчанию http://localhost:8000)")
    parser.add_argument("--images", type=Path, default=HERE / "images", help="папка с фотографиями")
    parser.add_argument("--baseline", type=Path, default=HERE / "expected" / "baseline.json", help="файл с эталоном")
    parser.add_argument("--timeout", type=float, default=60.0, help="таймаут одного запроса, секунды")
    args = parser.parse_args()

    if not args.images.is_dir():
        print(f"Нет папки с фотографиями: {args.images}")
        return 2
    images = collect_images(args.images)
    if not images:
        print(f"В {args.images} нет фотографий ({', '.join(sorted(IMAGE_EXTENSIONS))}). Положите туда 8-10 снимков.")
        return 2

    results, timings = run(args.url.rstrip("/"), images, args.timeout)
    print_timings(timings)

    failed = [name for name, eps in results.items() for ep, r in eps.items() if "http_error" in r]
    if failed:
        print(f"\nВНИМАНИЕ: для {len(failed)} запросов получена HTTP-ошибка, проверьте, что backend запущен.")

    if args.mode == "record":
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nЭталон сохранён: {args.baseline}")
        return 1 if failed else 0

    if not args.baseline.is_file():
        print(f"\nНет файла эталона {args.baseline}. Сначала выполните: python tests/snapshot.py record")
        return 2
    expected = json.loads(args.baseline.read_text(encoding="utf-8"))
    problems = compare(expected, results)
    if problems:
        print(f"\nРАСХОЖДЕНИЯ С ЭТАЛОНОМ ({len(problems)}):")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"\nOK: все ответы совпали с эталоном ({len(expected)} фото, допуск по уверенности {CONFIDENCE_TOLERANCE} п.п.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
