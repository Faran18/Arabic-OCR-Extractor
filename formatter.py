import os


def detect_alignment(bbox, page_width):
    x0, _, x1, _ = bbox
    center_x    = (x0 + x1) / 2
    page_center = page_width / 2
    right_gap   = page_width - x1
    left_gap    = x0

    if abs(center_x - page_center) < page_width * 0.1:
        return "center"
    elif right_gap < left_gap:
        return "right"
    else:
        return "left"


def export_to_html(matched_lines, output_path="output/result.html"):
    os.makedirs("output", exist_ok=True)

    html = ["""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>Extracted Arabic Text</title>
  <style>
    body {
      font-family: 'Arial', 'Tahoma', sans-serif;
      background: #f0f0f0;
      padding: 40px;
      direction: rtl;
    }
    .page {
      background: white;
      width: 620px;
      margin: 0 auto;
      padding: 60px 50px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      border-radius: 6px;
    }
    .line {
      font-size: 22px;
      line-height: 2.0;
      color: #1a1a1a;
      text-align: right;     /* Arabic is right-aligned */
      border-bottom: 1px solid #eee;   /* mimic notebook lines */
      padding: 4px 0;
    }
    .dim { color: #bbb; }
  </style>
</head>
<body>
<div class="page">
"""]

    for line in matched_lines:
        text       = line["text"]
        confidence = line.get("confidence", 1.0)
        dim        = " dim" if confidence < 0.5 else ""
        html.append(
            f'  <div class="line{dim}" '
            f'title="{confidence:.0%} confident">'
            f'{text}</div>\n'
        )

    html.append("</div>\n</body>\n</html>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(html)
    print(f"   → HTML saved: {output_path}")

def export_to_text(matched_lines, output_path="output/result.txt"):
    os.makedirs("output", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for line in matched_lines:
            f.write(line["text"] + "\n")

    print(f"   → Text saved: {output_path}")


def export_summary(matched_lines, output_path="output/summary.txt"):
    os.makedirs("output", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("LINE SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        for i, line in enumerate(matched_lines):
            f.write(f"Line {i+1}\n")
            f.write(f"  Text:       {line['text']}\n")
            f.write(f"  Confidence: {line.get('confidence', 'N/A')}\n")
            f.write(f"  BBox:       {line.get('bbox')}\n")
            f.write(f"  Match score:{line.get('match_score', 'N/A')}\n\n")

    print(f"   → Summary saved: {output_path}")