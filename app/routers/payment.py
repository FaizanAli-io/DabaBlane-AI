import httpx
from fastapi.responses import HTMLResponse
from fastapi import APIRouter, HTTPException

from tools.config import BASEURLFRONT
from tools.utils import get_auth_headers

router = APIRouter()


@router.get("/payment-page/{reference}", response_class=HTMLResponse)
async def generate_payment_page(reference: str):
    pay_url = f"{BASEURLFRONT}/payment/cmi/initiate"
    try:
        async with httpx.AsyncClient() as client:
            pay_res = await client.post(
                pay_url,
                headers=get_auth_headers(),
                json={"number": reference},
            )
            pay_res.raise_for_status()
            pay_data = pay_res.json()
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Error calling initiate API: {str(e)}"
        )

    if not pay_data.get("status") or "inputs" not in pay_data:
        raise HTTPException(status_code=400, detail="Invalid payment response")

    action = pay_data["payment_url"]
    method = pay_data["method"].lower()
    inputs = pay_data["inputs"]

    html_inputs = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}">' for k, v in inputs.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Redirecting to Payment...</title>
</head>
<body onload="document.forms[0].submit()">
  <p>Redirecting to secure payment...</p>
  <form method="{method}" action="{action}">
    {html_inputs}
  </form>
</body>
</html>"""

    return HTMLResponse(content=html)
