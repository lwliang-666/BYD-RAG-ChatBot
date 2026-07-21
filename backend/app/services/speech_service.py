"""
讯飞语音听写服务模块

调用讯飞语音听写（流式版）WebSocket API，将音频转为文字。
鉴权方式：hmac-sha256 签名。
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse

import websockets

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 讯飞语音听写 API 地址
IAT_URL = "wss://iat-api.xfyun.cn/v2/iat"


def _create_auth_url(api_key: str, api_secret: str) -> str:
    """生成讯飞 WebSocket API 鉴权 URL

    鉴权流程：
    1. 拼接签名原文：host + date + request-line
    2. 使用 api_secret 对签名原文做 hmac-sha256 签名
    3. 将签名结果 base64 编码后拼入 authorization 参数
    """
    url_obj = urlparse(IAT_URL)
    host = url_obj.hostname
    path = url_obj.path

    # RFC1123 格式的时间戳
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 拼接签名原文
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

    # hmac-sha256 签名
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")

    # 拼接 authorization 原文
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )

    # base64 编码
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    # 拼接完整 URL
    params = urlencode({"host": host, "date": date, "authorization": authorization})
    return f"{IAT_URL}?{params}"


async def speech_to_text(audio_data: bytes) -> str:
    """将音频数据发送到讯飞语音听写 API，返回识别文字

    参数：
        audio_data: PCM 16k 16bit 单声道的原始音频数据

    返回：
        识别出的文字字符串，识别失败返回空字符串
    """
    settings = get_settings()

    if not settings.XFYUN_APP_ID or not settings.XFYUN_API_KEY or not settings.XFYUN_API_SECRET:
        logger.error("讯飞语音听写配置缺失，请检查 XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET")
        return ""

    auth_url = _create_auth_url(settings.XFYUN_API_KEY, settings.XFYUN_API_SECRET)

    # 将音频 base64 编码
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    # 分帧参数：每帧 1280 字节（PCM 16k 16bit 单声道 40ms）
    frame_size = 1280
    audio_bytes = audio_data
    total_frames = (len(audio_bytes) + frame_size - 1) // frame_size

    result_text = ""

    try:
        async with websockets.connect(auth_url) as ws:
            # 首帧：发送公共参数 + 业务参数 + 首帧音频
            first_frame_data = audio_bytes[:frame_size]
            first_frame_b64 = base64.b64encode(first_frame_data).decode("utf-8")

            start_request = {
                "common": {"app_id": settings.XFYUN_APP_ID},
                "business": {
                    "language": "zh_cn",
                    "domain": "iat",
                    "accent": "mandarin",
                    "dwa": "wpgs",  # 开启动态修正
                },
                "data": {
                    "status": 0,
                    "format": "audio/L16;rate=16000",
                    "encoding": "raw",
                    "audio": first_frame_b64,
                },
            }
            await ws.send(json.dumps(start_request))

            # 中间帧：分帧发送剩余音频
            for i in range(1, total_frames):
                offset = i * frame_size
                frame_data = audio_bytes[offset : offset + frame_size]
                frame_b64 = base64.b64encode(frame_data).decode("utf-8")

                mid_request = {
                    "data": {
                        "status": 1,
                        "format": "audio/L16;rate=16000",
                        "encoding": "raw",
                        "audio": frame_b64,
                    }
                }
                await ws.send(json.dumps(mid_request))

            # 结束帧
            end_request = {"data": {"status": 2}}
            await ws.send(json.dumps(end_request))

            # 接收识别结果
            while True:
                response = await asyncio.wait_for(ws.recv(), timeout=30)
                resp_data = json.loads(response)

                code = resp_data.get("code", -1)
                if code != 0:
                    logger.error(f"讯飞语音听写错误: code={code}, message={resp_data.get('message', '')}")
                    break

                data = resp_data.get("data", {})
                result = data.get("result", {})
                ws_list = result.get("ws", [])

                for ws_item in ws_list:
                    for cw_item in ws_item.get("cw", []):
                        result_text += cw_item.get("w", "")

                # 识别结束
                if data.get("status") == 2:
                    break

    except asyncio.TimeoutError:
        logger.error("讯飞语音听写超时")
    except Exception as e:
        logger.error(f"讯飞语音听写异常: {e}")

    return result_text
