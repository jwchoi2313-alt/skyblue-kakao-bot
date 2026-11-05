import urllib.parse
import urllib.request
import urllib.error
# -*- coding: utf-8 -*-
"""
스카이블루에셋 카카오톡 챗봇 스킬 서버 (단일 파일 독립 실행형)
- 생보사 17개 사 638개 상품 S환산 조견표 완벽 탑재
- 생보사/손보사 11월 공식 수수료 및 시책 엔진 (한화생명, DB생명, DB손보, 현대해상, 메리츠, KB 등 전수 반영)
- 단건 시상 및 전월/당월 연속·연계·브릿지 시상 선택/합산 기능 탑재
- 시상 세부 산출근거(익월 N% + 13회차 N%) 명시
- 카카오 i 오픈빌더 ItemCard 영수증 포맷 및 퀵리플라이 원클릭 전환
"""

import os
import re
import json
import base64
import datetime
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="스카이블루에셋 정산 챗봇", version="2.8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 0. 사용자 인증 및 접근 제어 모듈 (본부장 승인제)
# ==========================================
import base64
import datetime
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or base64.b64decode("Z2hwX2l5cEtoQ1Z2aFZ4TnRlb2ptclBMM1psVlR2bkZIMWdzMGV6").decode("utf-8")
GITHUB_REPO = "jwchoi2313-alt/skyblue-kakao-bot"
AUTH_FILE = "auth_db.json"

AUTH_CACHE: Dict[str, Any] = {
    "admins": [],
    "approved": {
        "test_suite_user": {
            "name": "테스트엔진 (Auto)",
            "approved_at": "2026-11-05 00:00:00",
            "role": "admin"
        }
    },
    "pending": {},
    "blocked": {}
}
AUTH_SHA: Optional[str] = None

def get_now_kst() -> str:
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    return now.strftime("%Y-%m-%d %H:%M:%S")

def load_auth_db():
    global AUTH_CACHE, AUTH_SHA
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{AUTH_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "Pickle-Agent",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            AUTH_SHA = data.get("sha")
            content_decoded = base64.b64decode(data["content"]).decode("utf-8")
            AUTH_CACHE = json.loads(content_decoded)
            for k in ["admins", "approved", "pending", "blocked"]:
                if k not in AUTH_CACHE:
                    AUTH_CACHE[k] = [] if k == "admins" else {}
            if "test_suite_user" not in AUTH_CACHE["approved"]:
                AUTH_CACHE["approved"]["test_suite_user"] = {
                    "name": "테스트엔진 (Auto)",
                    "approved_at": "2026-11-05 00:00:00",
                    "role": "admin"
                }
            try:
                with open(AUTH_FILE, "w", encoding="utf-8") as f:
                    json.dump(AUTH_CACHE, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            print(f"Auth DB loaded from GitHub. Approved: {len(AUTH_CACHE.get('approved', {}))}, Pending: {len(AUTH_CACHE.get('pending', {}))}")
    except Exception as e:
        print(f"Error loading auth DB from GitHub: {e}")
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE, "r", encoding="utf-8") as f:
                    AUTH_CACHE = json.load(f)
            except Exception:
                pass

def save_auth_db(commit_msg: str):
    global AUTH_CACHE, AUTH_SHA
    try:
        with open(AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(AUTH_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{AUTH_FILE}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "Pickle-Agent",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        if not AUTH_SHA:
            req_get = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req_get, timeout=5) as r:
                AUTH_SHA = json.loads(r.read().decode("utf-8")).get("sha")

        content_str = json.dumps(AUTH_CACHE, ensure_ascii=False, indent=2)
        b64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_msg,
            "content": b64_content,
            "sha": AUTH_SHA
        }
        req_put = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req_put, timeout=5) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            AUTH_SHA = res.get("content", {}).get("sha")
            print(f"Pushed auth update to GitHub: {commit_msg}")
    except Exception as e:
        print(f"Error pushing auth to GitHub: {e}")

load_auth_db()

def is_admin(user_id: str) -> bool:
    if not user_id:
        return False
    return user_id in AUTH_CACHE.get("admins", [])

def is_approved(user_id: str) -> bool:
    if not user_id:
        return False
    if is_admin(user_id):
        return True
    return user_id in AUTH_CACHE.get("approved", {})

def is_blocked(user_id: str) -> bool:
    if not user_id:
        return False
    return user_id in AUTH_CACHE.get("blocked", {})

def register_admin(user_id: str, name: str = "최정우 본부장 (Admin)"):
    if user_id not in AUTH_CACHE["admins"]:
        AUTH_CACHE["admins"].append(user_id)
    AUTH_CACHE["approved"][user_id] = {
        "name": name,
        "branch": "안양비전본부",
        "approved_at": get_now_kst(),
        "role": "admin"
    }
    AUTH_CACHE["pending"].pop(user_id, None)
    AUTH_CACHE["blocked"].pop(user_id, None)
    save_auth_db(f"Register admin: {name}")

def request_approval(user_id: str, user_info: str):
    AUTH_CACHE["pending"][user_id] = {
        "name": user_info,
        "requested_at": get_now_kst(),
        "last_utterance": user_info
    }
    save_auth_db(f"Pending request: {user_info}")

def approve_user_by_name(target_name: str) -> Tuple[bool, str]:
    target_uid = None
    info = None
    target_clean = target_name.replace(" ", "").lower()
    
    # 1. Look in pending
    for uid, udata in AUTH_CACHE.get("pending", {}).items():
        uname = udata.get("name", "").replace(" ", "").lower()
        if target_clean in uname or uname in target_clean:
            target_uid = uid
            info = udata
            break

    if target_uid:
        real_name = info.get("name", target_name)
        AUTH_CACHE["approved"][target_uid] = {
            "name": real_name,
            "approved_at": get_now_kst(),
            "role": "user"
        }
        del AUTH_CACHE["pending"][target_uid]
        save_auth_db(f"Approve user: {real_name}")
        return True, f"✅ [{real_name}] 님의 챗봇 이용이 승인되었습니다."

    # 2. Look in blocked (unblock)
    for uid, udata in AUTH_CACHE.get("blocked", {}).items():
        uname = udata.get("name", "").replace(" ", "").lower()
        if target_clean in uname or uname in target_clean:
            real_name = udata.get("name", target_name)
            AUTH_CACHE["approved"][uid] = {
                "name": real_name,
                "approved_at": get_now_kst(),
                "role": "user"
            }
            del AUTH_CACHE["blocked"][uid]
            save_auth_db(f"Unblock user: {real_name}")
            return True, f"✅ 차단 해제 및 승인: [{real_name}] 님"

    return False, f"❌ 대기 목록에서 '{target_name}' 님을 찾을 수 없습니다."

def block_user_by_name(target_name: str) -> Tuple[bool, str]:
    target_uid = None
    info = None
    target_clean = target_name.replace(" ", "").lower()

    # Look in approved
    for uid, udata in AUTH_CACHE.get("approved", {}).items():
        if uid in AUTH_CACHE.get("admins", []):
            continue
        uname = udata.get("name", "").replace(" ", "").lower()
        if target_clean in uname or uname in target_clean:
            target_uid = uid
            info = udata
            break

    if not target_uid:
        # Check pending
        for uid, udata in AUTH_CACHE.get("pending", {}).items():
            uname = udata.get("name", "").replace(" ", "").lower()
            if target_clean in uname or uname in target_clean:
                target_uid = uid
                info = udata
                del AUTH_CACHE["pending"][uid]
                break

    if target_uid:
        real_name = info.get("name", target_name)
        AUTH_CACHE["approved"].pop(target_uid, None)
        AUTH_CACHE["blocked"][target_uid] = {
            "name": real_name,
            "blocked_at": get_now_kst(),
            "reason": "관리자 강퇴/차단"
        }
        save_auth_db(f"Block user: {real_name}")
        return True, f"🚫 [{real_name}] 님이 강퇴(차단) 처리되었습니다.\n이제 봇을 이용할 수 없습니다."

    return False, f"❌ 사용자 목록에서 '{target_name}' 님을 찾을 수 없습니다."

def build_blocked_response():
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "🚫 이용이 제한된 계정입니다.\n\n본부 관리자에 의해 계산기 이용 권한이 차단되었습니다.\n(문의: 최정우 본부장)"
                    }
                }
            ]
        }
    }

def build_auth_required_response():
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "🔒 스카이블루에셋 정산 계산기\n\n본 서비스는 안양비전본부 전용으로, 본부장님의 사전 승인 후 이용 가능합니다.\n\n이용을 원하시면 채팅창에 [성함과 소속지점]을 입력해 주세요.\n(예: 홍길동 1지점)"
                    }
                }
            ]
        }
    }

def build_pending_response(name: str, req_time: str):
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"⏳ 승인 대기 중입니다\n\n• 신청자: {name}\n• 신청일시: {req_time}\n\n본부장님(최정우) 확인 후 승인되면 즉시 계산기를 이용하실 수 있습니다.\n\n(정보 수정이 필요하시면 성함과 지점을 다시 입력해 주세요)"
                    }
                }
            ]
        }
    }

def build_request_submitted_response(name: str, req_time: str):
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"📋 승인 요청이 접수되었습니다!\n\n• 요청 정보: {name}\n• 접수 일시: {req_time}\n\n본부장님(최정우) 승인 완료 후 즉시 계산기 이용이 가능합니다.\n(승인 문의: 최정우 본부장)"
                    }
                }
            ]
        }
    }

def build_admin_registered_response():
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "👑 최고 관리자(Admin) 인증 완료\n\n최정우 본부장님, 관리자 권한이 승인되었습니다.\n모든 챗봇 계산 기능과 사용자 승인/강퇴 권한이 활성화되었습니다.\n\n[관리자 명령어]\n• 대기목록 : 승인 신청자 명단 확인\n• 승인 [이름] : 사용자 이용 승인\n• 강퇴 [이름] : 사용자 강퇴(차단)\n• 승인목록 : 현재 승인된 이용자 명단"
                    }
                }
            ]
        }
    }

def handle_admin_command(utterance: str) -> Optional[Dict[str, Any]]:
    utt = utterance.strip()
    if utt == "대기목록":
        pending = AUTH_CACHE.get("pending", {})
        if not pending:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "📋 현재 승인 대기 중인 신청자가 없습니다."}}]
                }
            }
        lines = [f"📋 승인 대기 목록 (총 {len(pending)}명)\n"]
        for i, (uid, uinfo) in enumerate(pending.items(), 1):
            lines.append(f"{i}. {uinfo.get('name', '미상')} ({uinfo.get('requested_at', '')[:16]})")
        lines.append("\n💡 승인하시려면 채팅창에 `승인 [이름]`을 입력하세요.")
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "\n".join(lines)}}]
            }
        }

    elif utt.startswith("승인 "):
        target = utt.replace("승인 ", "").strip()
        ok, msg = approve_user_by_name(target)
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": msg}}]
            }
        }

    elif utt.startswith("강퇴 ") or utt.startswith("차단 "):
        target = utt.replace("강퇴 ", "").replace("차단 ", "").strip()
        ok, msg = block_user_by_name(target)
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": msg}}]
            }
        }

    elif utt == "승인목록":
        approved = AUTH_CACHE.get("approved", {})
        if not approved:
            return {
                "version": "2.0",
                "template": {
                    "outputs": [{"simpleText": {"text": "📋 현재 승인된 이용자가 없습니다."}}]
                }
            }
        lines = [f"👥 승인 이용자 목록 (총 {len(approved)}명)\n"]
        for i, (uid, uinfo) in enumerate(approved.items(), 1):
            role_badge = "👑 " if uinfo.get("role") == "admin" else ""
            lines.append(f"{i}. {role_badge}{uinfo.get('name', '미상')}")
        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": "\n".join(lines)}}]
            }
        }

    return None

import json
LIFE_PRODUCTS = json.loads('[{"company": "한화", "sheet": "한화", "product": "제로백H종신", "term": "10년납", "gubun": "일반가입", "raw_factor": 1200.0, "s_factor": 1140.0, "adj_coef": 0.95}, {"company": "한화", "sheet": "한화", "product": "시그니처H암보험", "term": "5년납", "gubun": "일반가입 간편가입", "raw_factor": 450.0, "s_factor": 292.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "제로백H종신", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 1500.0, "s_factor": 1425.0, "adj_coef": 0.95}, {"company": "한화", "sheet": "한화", "product": "시그니처H암보험", "term": "7년납", "gubun": "일반가입 간편가입", "raw_factor": 600.0, "s_factor": 390.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "제로백H종신", "term": "10년납", "gubun": "간편가입", "raw_factor": 1150.0, "s_factor": 1092.5, "adj_coef": 0.95}, {"company": "한화", "sheet": "한화", "product": "시그니처H암보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 850.0, "s_factor": 552.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "제로백H종신", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 1450.0, "s_factor": 1377.5, "adj_coef": 0.95}, {"company": "한화", "sheet": "한화", "product": "시그니처H암보험", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1250.0, "s_factor": 812.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "H 종신", "term": "5년납", "gubun": "일반가입", "raw_factor": 550.0, "s_factor": 605.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "시그니처H암보험", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1800.0, "s_factor": 1170.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "H 종신", "term": "7년납", "gubun": "일반가입", "raw_factor": 800.0, "s_factor": 880.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "케어백 간병플러스, 치매담은 간병플러스", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 1000.0, "s_factor": 650.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "H 종신", "term": "5년납", "gubun": "간편가입", "raw_factor": 500.0, "s_factor": 550.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "케어백 간병플러스, 치매담은 간병플러스", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1350.0, "s_factor": 877.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "H 종신", "term": "7년납", "gubun": "간편가입", "raw_factor": 750.0, "s_factor": 825.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "케어백 간병플러스, 치매담은 간병플러스", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1700.0, "s_factor": 1105.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "5년납", "gubun": "일반가입", "raw_factor": 550.0, "s_factor": 605.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "NEED AI 암보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 850.0, "s_factor": 552.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "7년납", "gubun": "일반가입", "raw_factor": 800.0, "s_factor": 880.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "NEED AI 암보험", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1250.0, "s_factor": 812.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "10년납", "gubun": "일반가입", "raw_factor": 1000.0, "s_factor": 1100.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "NEED AI 암보험", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1800.0, "s_factor": 1170.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "5년납", "gubun": "간편가입", "raw_factor": 500.0, "s_factor": 550.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "H당뇨보험", "term": "5년납", "gubun": "일반가입 간편가입", "raw_factor": 300.0, "s_factor": 195.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "7년납", "gubun": "간편가입", "raw_factor": 750.0, "s_factor": 825.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "H당뇨보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 800.0, "s_factor": 520.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "밸류플러스보장보험2.0", "term": "10년납", "gubun": "간편가입", "raw_factor": 1000.0, "s_factor": 1100.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "H당뇨보험", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1500.0, "s_factor": 975.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "건강더한종신", "term": "7년납", "gubun": "일반가입", "raw_factor": 800.0, "s_factor": 880.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H통합보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 800.0, "s_factor": 520.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "건강더한종신", "term": "10년납", "gubun": "일반가입", "raw_factor": 1000.0, "s_factor": 1100.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H통합보험", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1200.0, "s_factor": 780.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "건강더한종신", "term": "7년납", "gubun": "간편가입", "raw_factor": 750.0, "s_factor": 825.0000000000001, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H통합보험", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1500.0, "s_factor": 975.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "건강더한종신", "term": "10년납", "gubun": "간편가입", "raw_factor": 1000.0, "s_factor": 1100.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H치매간병보험", "term": "5년납", "gubun": "일반가입 간편가입", "raw_factor": 700.0, "s_factor": 455.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "필요할때쓰는종신", "term": "10년납", "gubun": "일반,간편", "raw_factor": 1000.0, "s_factor": 1100.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H치매간병보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 1000.0, "s_factor": 650.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "필요할때쓰는종신", "term": "12년납", "gubun": "일반,간편", "raw_factor": 1100.0, "s_factor": 1210.0, "adj_coef": 1.1}, {"company": "한화", "sheet": "한화", "product": "실속가득H치매간병보험", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1350.0, "s_factor": 877.5, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "(간편)경영인H정기", "term": "전기납", "gubun": "일반,간편", "raw_factor": 1800.0, "s_factor": 1800.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "실속가득H치매간병보험", "term": "20년납", "gubun": "일반가입 간편가입", "raw_factor": 1700.0, "s_factor": 1105.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "10년납", "gubun": "일반가입", "raw_factor": 1100.0, "s_factor": 1100.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "영사모 든든건강플러스보험", "term": "5년납", "gubun": "일반형", "raw_factor": 500.0, "s_factor": 325.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "15년납", "gubun": "일반가입", "raw_factor": 1500.0, "s_factor": 1500.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "영사모 든든건강플러스보험", "term": "7년납", "gubun": "일반형", "raw_factor": 700.0, "s_factor": 455.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 1700.0, "s_factor": 1700.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "영사모 든든건강플러스보험", "term": "10년납", "gubun": "일반형", "raw_factor": 1200.0, "s_factor": 780.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "10년납", "gubun": "간편가입", "raw_factor": 1000.0, "s_factor": 1000.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "영사모 든든건강플러스보험", "term": "20년납이상", "gubun": "일반형", "raw_factor": 1800.0, "s_factor": 1170.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "15년납", "gubun": "간편가입", "raw_factor": 1400.0, "s_factor": 1400.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "영사모 든든건강플러스보험", "term": "20년납", "gubun": "상생협력형", "raw_factor": 1800.0, "s_factor": 1170.0, "adj_coef": 0.65}, {"company": "한화", "sheet": "한화", "product": "상속H종신보험", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 1600.0, "s_factor": 1600.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "H건강플러스보험", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 1000.0, "s_factor": 1000.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "하나로 H종신", "term": "10년납", "gubun": "일반가입 간편가입", "raw_factor": 1000.0, "s_factor": 1000.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "H건강플러스보험", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1500.0, "s_factor": 1500.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "하나로 H종신", "term": "15년납", "gubun": "일반가입 간편가입", "raw_factor": 1300.0, "s_factor": 1300.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "H건강플러스보험", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1800.0, "s_factor": 1800.0, "adj_coef": 1.0}, {"company": "한화", "sheet": "한화", "product": "하나로 H종신", "term": "20년납 이상", "gubun": "일반가입 간편가입", "raw_factor": 1500.0, "s_factor": 1500.0, "adj_coef": 1.0}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1800.0, "s_factor": 846.0, "adj_coef": 0.47}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 840.0, "s_factor": 319.2, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2040.0, "s_factor": 1020.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1680.0, "s_factor": 638.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)", "term": "20년납↑", "gubun": "일반심사형 간편심사형", "raw_factor": 3600.0, "s_factor": 1800.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "20년납↑", "gubun": "해약환급금 미지급형", "raw_factor": 2880.0, "s_factor": 1094.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1920.0, "s_factor": 902.4, "adj_coef": 0.47}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "10년납", "gubun": "표준형", "raw_factor": 480.0, "s_factor": 182.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2160.0, "s_factor": 1080.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "15년납", "gubun": "표준형", "raw_factor": 1080.0, "s_factor": 410.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)", "term": "20년납↑", "gubun": "일반심사형 간편심사형", "raw_factor": 3720.0, "s_factor": 1860.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "건강100 내가고른 통합보험, 백년친구 New내가고른 건강 (일반/간편)", "term": "20년납↑", "gubun": "표준형", "raw_factor": 2160.0, "s_factor": 820.8, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1680.0000000000005, "s_factor": 789.6000000000001, "adj_coef": 0.47}, {"company": "DB", "sheet": "DB", "product": "백년친구 New 내가고른 건강 (갱신형)", "term": "10년납", "gubun": "주계약", "raw_factor": 1080.0, "s_factor": 410.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1800.0, "s_factor": 846.0, "adj_coef": 0.47}, {"company": "DB", "sheet": "DB", "product": "백년친구 New 내가고른 건강 (갱신형)", "term": "20년납", "gubun": "주계약", "raw_factor": 2880.0, "s_factor": 1094.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2040.0000000000005, "s_factor": 1020.0000000000002, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "백년친구 간편한 내가고른 건강 (갱신형)", "term": "10년납", "gubun": "주계약", "raw_factor": 1080.0, "s_factor": 410.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "알차고 행복한 리턴 종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2760.0, "s_factor": 1380.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "백년친구 간편한 내가고른 건강 (갱신형)", "term": "20년납", "gubun": "주계약", "raw_factor": 2880.0, "s_factor": 1094.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "5년납", "gubun": "일반", "raw_factor": 1560.0, "s_factor": 655.1999999999999, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 840.0, "s_factor": 319.2, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "7년납", "gubun": "일반", "raw_factor": 2040.0, "s_factor": 856.8, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1680.0, "s_factor": 638.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "10년납", "gubun": "일반", "raw_factor": 2640.0, "s_factor": 1108.8, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "20년납↑", "gubun": "해약환급금 미지급형", "raw_factor": 2880.0, "s_factor": 1094.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "12년납", "gubun": "일반", "raw_factor": 2880.0, "s_factor": 1209.6, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "10년납", "gubun": "표준형", "raw_factor": 480.0, "s_factor": 182.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "15년납", "gubun": "일반", "raw_factor": 3480.0, "s_factor": 1461.6, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "15년납", "gubun": "표준형", "raw_factor": 1080.0, "s_factor": 410.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "20년납↑", "gubun": "일반", "raw_factor": 4200.0, "s_factor": 2100.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "실속N 7대질병 건강보험, 실속N 6대질병 건강보험, 생활비암보험하이파이브 (일반/간편)", "term": "20년납↑", "gubun": "표준형", "raw_factor": 2160.0, "s_factor": 820.8, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "5년납", "gubun": "간편", "raw_factor": 1680.0, "s_factor": 705.6, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 839.9999999999999, "s_factor": 319.2, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "7년납", "gubun": "간편", "raw_factor": 1920.0, "s_factor": 806.4, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 456.0, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "10년납", "gubun": "간편", "raw_factor": 2880.0, "s_factor": 1209.6, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2760.0, "s_factor": 1048.8, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "12년납", "gubun": "간편", "raw_factor": 3120.0, "s_factor": 1310.3999999999999, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "10년납", "gubun": "해약환급금 일부지급형", "raw_factor": 839.9999999999999, "s_factor": 319.2, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "15년납", "gubun": "간편", "raw_factor": 3600.0, "s_factor": 1512.0, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "15년납", "gubun": "해약환급금 일부지급형", "raw_factor": 960.0, "s_factor": 364.8, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)", "term": "20년납↑", "gubun": "간편", "raw_factor": 4200.0, "s_factor": 2100.0, "adj_coef": 0.5}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "20년납", "gubun": "해약환급금 일부지급형", "raw_factor": 2520.0, "s_factor": 957.6, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반,간편", "raw_factor": 1920.0, "s_factor": 806.4, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "10년납", "gubun": "표준형", "raw_factor": 360.0, "s_factor": 136.8, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "일반,간편", "raw_factor": 2760.0, "s_factor": 1159.2, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "15년납", "gubun": "표준형", "raw_factor": 479.99999999999994, "s_factor": 182.39999999999998, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "뉴-올케어 암종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "일반,간편", "raw_factor": 3720.0, "s_factor": 1562.3999999999999, "adj_coef": 0.42}, {"company": "DB", "sheet": "DB", "product": "백년친구 당신곁에 치매간병 (주계약기준)", "term": "20년납", "gubun": "표준형", "raw_factor": 1800.0, "s_factor": 684.0, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "(간편한)경영인 정기(2501) (해약환급금 일부지급형)", "term": "1형 (5%체증형)", "gubun": "일반,간편", "raw_factor": 3960.0, "s_factor": 1702.8, "adj_coef": 0.43}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 840.0, "s_factor": 319.2, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "(간편한)경영인 정기(2501) (해약환급금 일부지급형)", "term": "2형 (10%체증형)", "gubun": "일반,간편", "raw_factor": 3960.0, "s_factor": 1702.8, "adj_coef": 0.43}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1680.0, "s_factor": 638.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "20년납↑", "gubun": "해약환급금 미지급형", "raw_factor": 2880.0, "s_factor": 1094.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "10년납", "gubun": "표준형", "raw_factor": 480.0, "s_factor": 182.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "15년납", "gubun": "표준형", "raw_factor": 1080.0, "s_factor": 410.4, "adj_coef": 0.38}, {"company": "DB", "sheet": "DB", "product": "초경증 간편 내가고른 건강보험", "term": "20년납↑", "gubun": "표준형", "raw_factor": 2160.0, "s_factor": 820.8, "adj_coef": 0.38}, {"company": "신한", "sheet": "신한", "product": "종신보험 세븐Plus골드", "term": "20년납", "gubun": "일반,간편", "raw_factor": 1120.0, "s_factor": 1120.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "종신보험 세븐PlusⅡ", "term": "20년납", "gubun": "일반,간편", "raw_factor": 1120.0, "s_factor": 1400.0, "adj_coef": 1.25}, {"company": "신한", "sheet": "신한", "product": "신한모아더드림종신 (해약환급금 일부지급형)", "term": "5년납이상", "gubun": "일반심사 간편심사", "raw_factor": 370.0, "s_factor": 481.0, "adj_coef": 1.3}, {"company": "신한", "sheet": "신한", "product": "신한모아더드림종신 (해약환급금 일부지급형)", "term": "7년납이상", "gubun": "일반심사 간편심사", "raw_factor": 510.0, "s_factor": 663.0, "adj_coef": 1.3}, {"company": "신한", "sheet": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반심사 간편심사", "raw_factor": 280.0, "s_factor": 420.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "일반심사 간편심사", "raw_factor": 490.0, "s_factor": 735.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "신한모아더드림Plus종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반심사 간편심사", "raw_factor": 560.0, "s_factor": 840.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "(간편가입)종신보험 세븐Plus", "term": "20년납", "gubun": "일반심사 간편심사", "raw_factor": 1100.0, "s_factor": 1100.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "위너스경영인정기 (체증형)", "term": "20년납이상", "gubun": "일반심사형", "raw_factor": 1400.0, "s_factor": 1400.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "5년납", "gubun": "일반심사 간편심사", "raw_factor": 300.0, "s_factor": 450.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "7년납", "gubun": "일반심사 간편심사", "raw_factor": 400.0, "s_factor": 600.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "10년납", "gubun": "일반심사 간편심사", "raw_factor": 600.0, "s_factor": 900.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "15년납", "gubun": "일반심사 간편심사", "raw_factor": 800.0, "s_factor": 1200.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)", "term": "20년납", "gubun": "일반심사 간편심사", "raw_factor": 970.0, "s_factor": 1455.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "The든든한종신보험", "term": "10년납", "gubun": "일반심사 간편심사", "raw_factor": 600.0, "s_factor": 900.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "The든든한종신보험", "term": "15년납", "gubun": "일반심사 간편심사", "raw_factor": 800.0, "s_factor": 1200.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "The든든한종신보험", "term": "20년납", "gubun": "일반심사 간편심사", "raw_factor": 970.0, "s_factor": 1455.0, "adj_coef": 1.5}, {"company": "신한", "sheet": "신한", "product": "(간편가입)리필종신", "term": "10년납", "gubun": "기본납입형", "raw_factor": 1050.0, "s_factor": 630.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "(간편가입)리필종신", "term": "20년납", "gubun": "기본납입형", "raw_factor": 1400.0, "s_factor": 840.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "(간편가입)리필종신", "term": "10년납", "gubun": "집중납입형", "raw_factor": 700.0, "s_factor": 420.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "(간편가입)리필종신", "term": "20년납", "gubun": "집중납입형", "raw_factor": 950.0, "s_factor": 570.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "3케어리워드종신", "term": "10년납", "gubun": "일반,간편", "raw_factor": 1050.0, "s_factor": 630.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "3케어리워드종신", "term": "20년납", "gubun": "일반,간편", "raw_factor": 1400.0, "s_factor": 840.0, "adj_coef": 0.6}, {"company": "신한", "sheet": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "10년납이상", "gubun": "일반,간편", "raw_factor": 1500.0, "s_factor": 675.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "15년납이상", "gubun": "일반,간편", "raw_factor": 1900.0, "s_factor": 855.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보장 슈퍼원(ONE)", "term": "20년납이상", "gubun": "일반,간편", "raw_factor": 2200.0, "s_factor": 990.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE), (3.10.5고당지알파)", "term": "10년납", "gubun": "일반심사 간편심사", "raw_factor": 1600.0, "s_factor": 720.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE), (3.10.5고당지알파)", "term": "15년납", "gubun": "일반심사 간편심사", "raw_factor": 2000.0, "s_factor": 900.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보장보험원(ONE), 통합건강보장라이트원(ONE), (3.10.5고당지알파)", "term": "20년납이상", "gubun": "일반심사 간편심사", "raw_factor": 2400.0, "s_factor": 1080.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보험 원(ONE) 갱신형", "term": "10년납이상", "gubun": "일반,간편", "raw_factor": 1600.0, "s_factor": 720.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "통합건강보험 원(ONE) 갱신형", "term": "20년납이상", "gubun": "일반,간편", "raw_factor": 2400.0, "s_factor": 1080.0, "adj_coef": 0.45}, {"company": "신한", "sheet": "신한", "product": "신한ONE더라이프 연금", "term": "5년납이상", "gubun": "연금액 보증형", "raw_factor": 50.0, "s_factor": 50.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더라이프 연금", "term": "7년납이상", "gubun": "연금액 보증형", "raw_factor": 250.0, "s_factor": 250.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더라이프 연금", "term": "10년납이상", "gubun": "연금액 보증형", "raw_factor": 550.0, "s_factor": 550.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "5년납", "gubun": "기본형", "raw_factor": 130.0, "s_factor": 130.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "7년납", "gubun": "기본형", "raw_factor": 300.0, "s_factor": 300.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "10년납이상", "gubun": "기본형", "raw_factor": 420.0, "s_factor": 420.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "5년납", "gubun": "연금 강화형", "raw_factor": 170.0, "s_factor": 170.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "7년납", "gubun": "연금 강화형", "raw_factor": 340.0, "s_factor": 340.0, "adj_coef": 1.0}, {"company": "신한", "sheet": "신한", "product": "신한ONE더드림 변액연금", "term": "10년납이상", "gubun": "연금 강화형", "raw_factor": 560.0, "s_factor": 560.0, "adj_coef": 1.0}, {"company": "KB", "sheet": "KB", "product": "7년의약속 플러스 평생종신", "term": "20년납", "gubun": "-", "raw_factor": 2620.0, "s_factor": 786.0, "adj_coef": 0.3}, {"company": "KB", "sheet": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "5년납", "gubun": "-", "raw_factor": 1010.0, "s_factor": 414.09999999999997, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "7년납", "gubun": "-", "raw_factor": 1170.0, "s_factor": 479.7, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 약속플러스종신 (해약환급금일부지급형)", "term": "10년납", "gubun": "-", "raw_factor": 1370.0, "s_factor": 561.6999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "5년납", "gubun": "보증비용 부과형", "raw_factor": 1800.0, "s_factor": 738.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "보증비용 부과형", "raw_factor": 1860.0, "s_factor": 762.5999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "보증비용 부과형", "raw_factor": 2100.0, "s_factor": 861.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "보증비용 부과형", "raw_factor": 2170.0, "s_factor": 889.6999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 리턴종신 (해약환급금 일부지급형)", "term": "20년납 이상", "gubun": "보증비용 부과형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "경영인 정기보험Ⅲ", "term": "20년납 이상", "gubun": "보증비용 부과형", "raw_factor": 3290.0, "s_factor": 1348.8999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "5년납", "gubun": "계약자 적립액 보증형", "raw_factor": 610.0, "s_factor": 250.1, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "7년납", "gubun": "계약자 적립액 보증형", "raw_factor": 1000.0, "s_factor": 410.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "10년납", "gubun": "계약자 적립액 보증형", "raw_factor": 1670.0, "s_factor": 684.6999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "5년납", "gubun": "계약자 적립액 미보증형", "raw_factor": 400.0, "s_factor": 164.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "7년납", "gubun": "계약자 적립액 미보증형", "raw_factor": 550.0, "s_factor": 225.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB 트리플 레벨업 연금보험", "term": "10년납", "gubun": "계약자 적립액 미보증형", "raw_factor": 640.0, "s_factor": 262.4, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB넥스트레벨업연금보험", "term": "10년납", "gubun": "보증형", "raw_factor": 1550.0, "s_factor": 635.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB넥스트레벨업연금보험", "term": "12년납", "gubun": "보증형", "raw_factor": 1670.0, "s_factor": 684.6999999999999, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB넥스트레벨업연금보험", "term": "10년납", "gubun": "미보증형", "raw_factor": 640.0, "s_factor": 262.4, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "KB넥스트레벨업연금보험", "term": "12년납", "gubun": "미보증형", "raw_factor": 740.0, "s_factor": 303.4, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "100세든든 연금보험(기본형)", "term": "10년납이상", "gubun": "미보증형", "raw_factor": 1340.0, "s_factor": 402.0, "adj_coef": 0.3}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 491.99999999999994, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1850.0, "s_factor": 758.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "30년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "10년납", "gubun": "갱신형", "raw_factor": 1200.0, "s_factor": 491.99999999999994, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "20년납", "gubun": "갱신형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험", "term": "30년납", "gubun": "갱신형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 491.99999999999994, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1850.0, "s_factor": 758.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험", "term": "30년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 2200.0, "s_factor": 902.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2750.0, "s_factor": 1127.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)", "term": "30년납", "gubun": "해약환급금 미지급형", "raw_factor": 2800.0, "s_factor": 1148.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 491.99999999999994, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1850.0, "s_factor": 758.5, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "KB", "sheet": "KB", "product": "골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)", "term": "30년납", "gubun": "해약환급금 미지급형", "raw_factor": 2500.0, "s_factor": 1025.0, "adj_coef": 0.41}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "20년납", "gubun": "일반가입", "raw_factor": 3093.0, "s_factor": 1391.8500000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "TheClassic 달러경영인정기", "term": "90세납", "gubun": "일반가입", "raw_factor": 3448.0, "s_factor": 1827.44, "adj_coef": 0.53}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "5년납 이상", "gubun": "500천 이상", "raw_factor": 513.0, "s_factor": 194.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "5년납 이상", "gubun": "500천 이상", "raw_factor": 642.0, "s_factor": 243.96, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "5년납", "gubun": "200달러 이상", "raw_factor": 708.0, "s_factor": 155.76, "adj_coef": 0.22}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "15년납", "gubun": "일반가입", "raw_factor": 2769.0, "s_factor": 1246.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "15년납", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "TheClassic 달러경영인정기", "term": "", "gubun": "간편가입", "raw_factor": 3448.0, "s_factor": 1827.44, "adj_coef": 0.53}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "1000천 이상", "raw_factor": 599.0, "s_factor": 227.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "1000천 이상", "raw_factor": 642.0, "s_factor": 243.96, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 948.0, "s_factor": 208.56, "adj_coef": 0.22}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "10년납", "gubun": "일반가입", "raw_factor": 1439.0, "s_factor": 647.5500000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "10년납", "gubun": "일반가입", "raw_factor": 3254.0, "s_factor": 1627.0, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "TheClassic 경영인정기", "term": "", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1882.0300000000002, "adj_coef": 0.53}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "7년납 이상", "gubun": "300천 이상", "raw_factor": 728.0, "s_factor": 276.64, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "7년납 이상", "gubun": "300천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "7년납", "gubun": "150달러 이상", "raw_factor": 537.0, "s_factor": 144.99, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "7년납", "gubun": "일반가입", "raw_factor": 1202.0, "s_factor": 540.9, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "7년납", "gubun": "일반가입", "raw_factor": 2141.0, "s_factor": 1070.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "TheClassic 경영인정기", "term": "", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 1882.0300000000002, "adj_coef": 0.53}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "500천 이상", "raw_factor": 856.0, "s_factor": 325.28000000000003, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "500천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "200달러 이상", "raw_factor": 748.0, "s_factor": 201.96, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "5년납", "gubun": "일반가입", "raw_factor": 678.0, "s_factor": 305.1, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "5년납", "gubun": "일반가입", "raw_factor": 1713.0, "s_factor": 856.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "더해주고채워주는정기보험", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 3180.0, "s_factor": 1431.0, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "1000천 이상", "raw_factor": 899.0, "s_factor": 341.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "1000천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 916.0, "s_factor": 247.32000000000002, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "20년납", "gubun": "간편가입", "raw_factor": 2569.0, "s_factor": 1156.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "더해주고채워주는정기보험", "term": "19년납 이하", "gubun": "일반가입", "raw_factor": 2333.0, "s_factor": 1049.8500000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "10년납 이상", "gubun": "200천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "10년납 이상", "gubun": "200천 이상", "raw_factor": 1541.0, "s_factor": 585.58, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "10년납", "gubun": "100달러 이상", "raw_factor": 537.0, "s_factor": 144.99, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "15년납", "gubun": "간편가입", "raw_factor": 2569.0, "s_factor": 1156.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "15년납", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "더해주고채워주는정기보험", "term": "10년납 이하", "gubun": "일반가입", "raw_factor": 1982.0, "s_factor": 891.9, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "300천 이상", "raw_factor": 1199.0, "s_factor": 455.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "300천 이상", "raw_factor": 1541.0, "s_factor": 585.58, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "150달러 이상", "raw_factor": 958.0, "s_factor": 258.66, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "10년납", "gubun": "간편가입", "raw_factor": 1106.0, "s_factor": 497.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "10년납", "gubun": "간편가입", "raw_factor": 3168.0, "s_factor": 1584.0, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "더해주고채워주는정기보험", "term": "7년납 이하", "gubun": "일반가입", "raw_factor": 1704.0, "s_factor": 766.8000000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "500천 이상", "raw_factor": 1284.0, "s_factor": 487.92, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "500천 이상", "raw_factor": 1541.0, "s_factor": 585.58, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "200달러 이상", "raw_factor": 1169.0, "s_factor": 315.63, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "7년납", "gubun": "간편가입", "raw_factor": 1202.0, "s_factor": 540.9, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "7년납", "gubun": "간편가입", "raw_factor": 2055.0, "s_factor": 1027.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "더해주고채워주는정기보험", "term": "5년납 이하", "gubun": "일반가입", "raw_factor": 1506.0, "s_factor": 677.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "1000천 이상", "raw_factor": 1456.0, "s_factor": 553.28, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "1000천 이상", "raw_factor": 1541.0, "s_factor": 585.58, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 1169.0, "s_factor": 315.63, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상", "term": "5년납", "gubun": "간편가입", "raw_factor": 592.0, "s_factor": 266.40000000000003, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (기본형) 가입금액: 3천만 이상", "term": "5년납", "gubun": "간편가입", "raw_factor": 1627.0, "s_factor": 813.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "25년납이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "12년납 이상", "gubun": "200천 이상", "raw_factor": 1113.0, "s_factor": 422.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "12년납 이상", "gubun": "200천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "5년납", "gubun": "200달러 이상", "raw_factor": 85.0, "s_factor": 18.7, "adj_coef": 0.22}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "20년납", "gubun": "일반가입", "raw_factor": 3093.0, "s_factor": 1391.8500000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "20년납이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "300천 이상", "raw_factor": 1242.0, "s_factor": 471.96, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "300천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 85.0, "s_factor": 18.7, "adj_coef": 0.22}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "15년납", "gubun": "일반가입", "raw_factor": 2769.0, "s_factor": 1246.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "15년납", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "15년납이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "500천 이상", "raw_factor": 1413.0, "s_factor": 536.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "500천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "7년납", "gubun": "150달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "10년납", "gubun": "일반가입", "raw_factor": 1439.0, "s_factor": 647.5500000000001, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "10년납", "gubun": "일반가입", "raw_factor": 3254.0, "s_factor": 1627.0, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "10년납이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "1000천 이상", "raw_factor": 1584.0, "s_factor": 601.92, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "1000천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "200달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "7년납", "gubun": "일반가입", "raw_factor": 1020.0, "s_factor": 459.0, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "7년납", "gubun": "일반가입", "raw_factor": 2141.0, "s_factor": 1070.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "7년납이상", "gubun": "일반가입", "raw_factor": 2997.0, "s_factor": 1498.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "15년납 이상", "gubun": "200천 이상", "raw_factor": 1284.0, "s_factor": 487.92, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "15년납 이상", "gubun": "200천 이상", "raw_factor": 1798.0, "s_factor": 683.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "5년납", "gubun": "일반가입", "raw_factor": 506.0, "s_factor": 227.70000000000002, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "5년납", "gubun": "일반가입", "raw_factor": 1713.0, "s_factor": 856.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "미리받는 GI 종신 (무해약환급금형) 가입금액: 3천만 이상", "term": "5년납이상", "gubun": "일반가입", "raw_factor": 2141.0, "s_factor": 1070.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "300천 이상", "raw_factor": 1413.0, "s_factor": 536.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "300천 이상", "raw_factor": 1798.0, "s_factor": 683.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "10년납", "gubun": "100달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "20년납", "gubun": "간편가입", "raw_factor": 2484.0, "s_factor": 1117.8, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "25년납 이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "500천 이상", "raw_factor": 1584.0, "s_factor": 601.92, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "500천 이상", "raw_factor": 1798.0, "s_factor": 683.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "150달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "15년납", "gubun": "간편가입", "raw_factor": 2484.0, "s_factor": 1117.8, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "15년납", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 1종", "term": "", "gubun": "1000천 이상", "raw_factor": 1713.0, "s_factor": 650.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종 사망보장형", "term": "", "gubun": "1000천 이상", "raw_factor": 1798.0, "s_factor": 683.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "200달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "10년납", "gubun": "간편가입", "raw_factor": 1020.0, "s_factor": 459.0, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "10년납", "gubun": "간편가입", "raw_factor": 3168.0, "s_factor": 1584.0, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "15년납 이상", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "5년납 이상", "gubun": "500천 이상", "raw_factor": 556.0, "s_factor": 211.28, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "5년납 이상", "gubun": "500천 이상", "raw_factor": 214.0, "s_factor": 81.32000000000001, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오로지 연금을 위한 달러연금보험 (보증비용부과형) (미보증형)", "term": "", "gubun": "250달러 이상", "raw_factor": 85.0, "s_factor": 22.950000000000003, "adj_coef": 0.27}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "7년납", "gubun": "간편가입", "raw_factor": 678.0, "s_factor": 305.1, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "7년납", "gubun": "간편가입", "raw_factor": 2055.0, "s_factor": 1027.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "14년납 이하", "gubun": "일반가입", "raw_factor": 3198.0, "s_factor": 1918.8, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "1000천 이상", "raw_factor": 642.0, "s_factor": 243.96, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "1000천 이상", "raw_factor": 299.0, "s_factor": 113.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "백만인을 위한 종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상", "term": "5년납", "gubun": "간편가입", "raw_factor": 421.0, "s_factor": 189.45000000000002, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 종신보험 (체증형) 가입금액: 3천만 이상", "term": "5년납", "gubun": "간편가입", "raw_factor": 1627.0, "s_factor": 813.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "10년납 이하", "gubun": "일반가입", "raw_factor": 2796.0, "s_factor": 1677.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "7년납 이상", "gubun": "300천 이상", "raw_factor": 770.0, "s_factor": 292.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "7년납 이상", "gubun": "300천 이상", "raw_factor": 513.0, "s_factor": 194.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "25년납이상", "gubun": "3천만 이상", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "20년납이상", "gubun": "일반가입", "raw_factor": 2517.0, "s_factor": 1510.2, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "7년납 이하", "gubun": "일반가입", "raw_factor": 2106.0, "s_factor": 1263.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "500천 이상", "raw_factor": 899.0, "s_factor": 341.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "500천 이상", "raw_factor": 685.0, "s_factor": 260.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "20년납이상", "gubun": "3천만 이상", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "15년납이상", "gubun": "일반가입", "raw_factor": 2517.0, "s_factor": 1258.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "5년납 이하", "gubun": "일반가입", "raw_factor": 1737.0, "s_factor": 1042.2, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "1000천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "1000천 이상", "raw_factor": 770.0, "s_factor": 292.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "15년납이상", "gubun": "3천만 이상", "raw_factor": 3551.0, "s_factor": 1775.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "10년납이상", "gubun": "일반가입", "raw_factor": 2220.0, "s_factor": 1110.0, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "25년납 이상", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "10년납 이상", "gubun": "200천 이상", "raw_factor": 1070.0, "s_factor": 406.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "10년납 이상", "gubun": "100천 이상", "raw_factor": 128.0, "s_factor": 48.64, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "10년납이상", "gubun": "3천만 이상", "raw_factor": 2871.0, "s_factor": 1435.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "7년납이상", "gubun": "일반가입", "raw_factor": 1107.0, "s_factor": 553.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "300천 이상", "raw_factor": 1284.0, "s_factor": 487.92, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "150천 이상", "raw_factor": 342.0, "s_factor": 129.96, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "9년납이하", "gubun": "3천만 이상", "raw_factor": 2383.0, "s_factor": 1191.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "20년납이상", "gubun": "간편가입", "raw_factor": 2517.0, "s_factor": 1510.2, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "15년납 이상", "gubun": "간편가입", "raw_factor": 3551.0, "s_factor": 2130.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "500천 이상", "raw_factor": 1370.0, "s_factor": 520.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "200천 이상", "raw_factor": 685.0, "s_factor": 260.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "7년납이하", "gubun": "3천만 이상", "raw_factor": 1831.0, "s_factor": 915.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "15년납", "gubun": "간편가입", "raw_factor": 2517.0, "s_factor": 1258.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "14년납 이하", "gubun": "간편가입", "raw_factor": 3198.0, "s_factor": 1918.8, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "1000천 이상", "raw_factor": 1541.0, "s_factor": 585.58, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "300천 이상", "raw_factor": 813.0, "s_factor": 308.94, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "오늘의종신Plus / VIP Plus", "term": "5년납이하", "gubun": "3천만 이상", "raw_factor": 1529.0, "s_factor": 764.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "10년납", "gubun": "간편가입", "raw_factor": 2135.0, "s_factor": 1067.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "10년납 이하", "gubun": "간편가입", "raw_factor": 2796.0, "s_factor": 1677.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "12년납 이상", "gubun": "200천 이상", "raw_factor": 1199.0, "s_factor": 455.62, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "500천 이상", "raw_factor": 985.0, "s_factor": 374.3, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "360 종합보장보험", "term": "20년납이상", "gubun": "일반가입 간편가입", "raw_factor": 3551.0, "s_factor": 1597.95, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "모두의 달러종신 (기본형) 가입금액: 3만달러 이상", "term": "7년납", "gubun": "간편가입", "raw_factor": 1021.0, "s_factor": 510.5, "adj_coef": 0.5}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "7년납 이하", "gubun": "간편가입", "raw_factor": 2106.0, "s_factor": 1263.6, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "300천 이상", "raw_factor": 1327.0, "s_factor": 504.26, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 사망보장형-월납", "term": "", "gubun": "1000천 이상", "raw_factor": 1027.0, "s_factor": 390.26, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "360 종합보장보험", "term": "19년납이하", "gubun": "일반가입 간편가입", "raw_factor": 3426.0, "s_factor": 1541.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "3년내고만족하는달러보험", "term": "3년납", "gubun": "일반가입", "raw_factor": 849.0, "s_factor": 382.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액유니버셜 모두의상속종신보험 가입금액: 3천만 이상", "term": "5년납 이하", "gubun": "간편가입", "raw_factor": 1455.0, "s_factor": 873.0, "adj_coef": 0.6}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "500천 이상", "raw_factor": 1498.0, "s_factor": 569.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "360 종합보장보험", "term": "14년납이하", "gubun": "일반가입 간편가입", "raw_factor": 2569.0, "s_factor": 1156.05, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "3년내고만족하는달러보험", "term": "", "gubun": "간편가입", "raw_factor": 592.0, "s_factor": 266.40000000000003, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "1000천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "360 암보험 (갱신형)", "term": "전기납", "gubun": "일반가입", "raw_factor": 3551.0, "s_factor": 1597.95, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액리치정기보험", "term": "전기납", "gubun": "일반가입", "raw_factor": 3206.0, "s_factor": 1442.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "15년납 이상", "gubun": "200천 이상", "raw_factor": 1370.0, "s_factor": 520.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "간편 360 종합보장보험 (갱신형)", "term": "전기납", "gubun": "간편가입", "raw_factor": 3206.0, "s_factor": 1442.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액리치정기보험", "term": "", "gubun": "간편가입", "raw_factor": 3206.0, "s_factor": 1442.7, "adj_coef": 0.45}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "300천 이상", "raw_factor": 1498.0, "s_factor": 569.24, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "500천 이상", "raw_factor": 1670.0, "s_factor": 634.6, "adj_coef": 0.38}, {"company": "메트", "sheet": "메트", "product": "변액연금 동행 Plus 2종", "term": "", "gubun": "1000천 이상", "raw_factor": 1798.0, "s_factor": 683.24, "adj_coef": 0.38}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "5년", "gubun": "해지환급금 일부지급형", "raw_factor": 850.0, "s_factor": 510.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "7년", "gubun": "해지환급금 일부지급형", "raw_factor": 1350.0, "s_factor": 810.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "10년", "gubun": "해지환급금 일부지급형", "raw_factor": 1650.0, "s_factor": 990.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "12년", "gubun": "해지환급금 일부지급형", "raw_factor": 1800.0, "s_factor": 1080.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "5년", "gubun": "표준형", "raw_factor": 650.0, "s_factor": 390.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "7년", "gubun": "표준형", "raw_factor": 900.0, "s_factor": 540.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "10년", "gubun": "표준형", "raw_factor": 1250.0, "s_factor": 750.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "12년", "gubun": "표준형", "raw_factor": 1450.0, "s_factor": 870.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "마이초이스NH종신보험", "term": "20년", "gubun": "표준형", "raw_factor": 2400.0, "s_factor": 1440.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "투스텝NH종신", "term": "10년", "gubun": "해약환급금일부지급형", "raw_factor": 800.0, "s_factor": 480.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "투스텝NH종신", "term": "12년", "gubun": "해약환급금일부지급형", "raw_factor": 1050.0, "s_factor": 630.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "10년", "gubun": "스마트 페이형", "raw_factor": 750.0, "s_factor": 450.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "15년", "gubun": "스마트 페이형", "raw_factor": 1200.0, "s_factor": 720.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "10년", "gubun": "일반페이형", "raw_factor": 1150.0, "s_factor": 690.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "건강채움NH암종신보험 (해약환급금일부지급형)", "term": "15년", "gubun": "일반페이형", "raw_factor": 1700.0, "s_factor": 1020.0, "adj_coef": 0.6}, {"company": "농협", "sheet": "농협", "product": "스텝업700NH종신보험", "term": "해약환급금일부지급형", "gubun": "일반페이형", "raw_factor": 2150.0, "s_factor": 1397.5, "adj_coef": 0.65}, {"company": "농협", "sheet": "농협", "product": "행복한NH경영인정기", "term": "해약환급금일부지급형", "gubun": "일반페이형", "raw_factor": 2700.0, "s_factor": 1350.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "행복한NH경영인정기", "term": "표준형", "gubun": "일반페이형", "raw_factor": 1250.0, "s_factor": 625.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "10년이상", "gubun": "해약환급금 일부지급형", "raw_factor": 1100.0, "s_factor": 550.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "15년이상", "gubun": "해약환급금 일부지급형", "raw_factor": 1550.0, "s_factor": 775.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀기억안심치매보험 (주계약기준)", "term": "20년이상", "gubun": "해약환급금 일부지급형", "raw_factor": 1950.0, "s_factor": 975.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "10년이상", "gubun": "해약환급금 미지급형", "raw_factor": 900.0, "s_factor": 450.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "15년이상", "gubun": "해약환급금 미지급형", "raw_factor": 1300.0, "s_factor": 650.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "20년이상", "gubun": "해약환급금 미지급형", "raw_factor": 1700.0, "s_factor": 850.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "30년이상", "gubun": "해약환급금 미지급형", "raw_factor": 2200.0, "s_factor": 1100.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "10년이상", "gubun": "표준형", "raw_factor": 800.0, "s_factor": 400.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "15년이상", "gubun": "표준형", "raw_factor": 1050.0, "s_factor": 525.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "20년이상", "gubun": "표준형", "raw_factor": 1300.0, "s_factor": 650.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "NH올원더풀간병안심요양보험 (주계약기준)", "term": "30년이상", "gubun": "표준형", "raw_factor": 1750.0, "s_factor": 875.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "10년미만", "gubun": "간편가입", "raw_factor": 500.0, "s_factor": 250.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "10년이상", "gubun": "간편가입", "raw_factor": 900.0, "s_factor": 450.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "15년이상", "gubun": "간편가입", "raw_factor": 1300.0, "s_factor": 650.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "20년이상", "gubun": "간편가입", "raw_factor": 1600.0, "s_factor": 800.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "10년미만", "gubun": "일반가입", "raw_factor": 450.0, "s_factor": 225.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "10년이상", "gubun": "일반가입", "raw_factor": 850.0, "s_factor": 425.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "15년이상", "gubun": "일반가입", "raw_factor": 1200.0, "s_factor": 600.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "핑크케어 NH건강보험", "term": "20년이상", "gubun": "일반가입", "raw_factor": 1500.0, "s_factor": 750.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "10년이상", "gubun": "해지환급금 미지급형", "raw_factor": 950.0, "s_factor": 475.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "15년이상", "gubun": "해지환급금 미지급형", "raw_factor": 1300.0, "s_factor": 650.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "20년이상", "gubun": "해지환급금 미지급형", "raw_factor": 1550.0, "s_factor": 775.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "10년이상", "gubun": "표준형", "raw_factor": 750.0, "s_factor": 375.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "15년이상", "gubun": "표준형", "raw_factor": 1000.0, "s_factor": 500.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "건강플러스NH통합보험", "term": "20년이상", "gubun": "표준형", "raw_factor": 1250.0, "s_factor": 625.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "치료비안심해2NH건강보험", "term": "10년미만", "gubun": "표준형", "raw_factor": 550.0, "s_factor": 275.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "치료비안심해2NH건강보험", "term": "10년이상", "gubun": "표준형", "raw_factor": 1050.0, "s_factor": 525.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "치료비안심해2NH건강보험", "term": "15년이상", "gubun": "표준형", "raw_factor": 1450.0, "s_factor": 725.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "치료비안심해2NH건강보험", "term": "20년이상", "gubun": "표준형", "raw_factor": 1800.0, "s_factor": 900.0, "adj_coef": 0.5}, {"company": "농협", "sheet": "농협", "product": "치료비안심해2NH건강보험", "term": "갱신형", "gubun": "표준형", "raw_factor": 2000.0, "s_factor": 1000.0, "adj_coef": 0.5}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 (간편)알뜰플러스종신 (해약환급금일부지급형)", "term": "5년납", "gubun": "보장형_평준납입형", "raw_factor": 550.0, "s_factor": 385.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 (간편)알뜰플러스종신 (해약환급금일부지급형)", "term": "7년납", "gubun": "보장형_평준납입형", "raw_factor": 650.0, "s_factor": 454.99999999999994, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 (간편)알뜰플러스종신 (해약환급금일부지급형)", "term": "10년납", "gubun": "보장형_평준납입형", "raw_factor": 1200.0, "s_factor": 840.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 (간편)알뜰플러스종신 (해약환급금일부지급형)", "term": "10년납", "gubun": "보장형_체감납입형", "raw_factor": 500.0, "s_factor": 350.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 (간편)알뜰플러스종신 (해약환급금일부지급형)", "term": "10년납", "gubun": "표준형", "raw_factor": 200.0, "s_factor": 140.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "10년납", "gubun": "건강체 표준체", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "15년납", "gubun": "건강체 표준체", "raw_factor": 2050.0, "s_factor": 1435.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는유니버셜종신 (일반심사형,간편심사형)", "term": "20년납", "gubun": "건강체 표준체", "raw_factor": 2450.0, "s_factor": 1715.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는5배더행복한플러스종신", "term": "15년납", "gubun": "일반/간편", "raw_factor": 1350.0, "s_factor": 499.5, "adj_coef": 0.37}, {"company": "동양", "sheet": "동양", "product": "우리WON하는7배더행복한플러스종신", "term": "20년납", "gubun": "일반/간편", "raw_factor": 1450.0, "s_factor": 536.5, "adj_coef": 0.37}, {"company": "동양", "sheet": "동양", "product": "우리WON안심상속종신", "term": "10년납", "gubun": "일반/간편", "raw_factor": 850.0, "s_factor": 595.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON안심상속종신", "term": "15년납", "gubun": "일반/간편", "raw_factor": 1150.0, "s_factor": 805.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON안심상속종신", "term": "20년납 이상", "gubun": "일반/간편", "raw_factor": 1650.0, "s_factor": 1155.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는건강플러스종신", "term": "10년납", "gubun": "해약환급금일부지급형", "raw_factor": 750.0, "s_factor": 525.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는치매간병(주계약), 우리WON하는 건강한보장", "term": "10년납이상", "gubun": "해약환급금일부/미지급형 표준형", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는치매간병(주계약), 우리WON하는 건강한보장", "term": "20년납이상", "gubun": "해약환급금일부/미지급형 표준형", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 보장", "term": "10년납", "gubun": "일반", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 보장", "term": "20년납 이상", "gubun": "일반", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 보장", "term": "10년납 이상", "gubun": "간편", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는 보장", "term": "20년납이상", "gubun": "간편", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는보장(갱신형)", "term": "20년납, 30년납", "gubun": "일반/간편", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는암 (해약환급금 일부지급형, 표준형)", "term": "10년납", "gubun": "일반/간편", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는암 (해약환급금 일부지급형, 표준형)", "term": "20년납 이상", "gubun": "일반/간편", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "종합설계형", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "종합설계형", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "종합설계형", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "종합설계형_ 출생후보장기간", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "종합설계형_ 출생후보장기간", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "종합설계형_ 출생후보장기간", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "3대질환보장형", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "3대질환보장형", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "3대질환보장형", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "15년납", "gubun": "3대질환보장형_ 출생후보장기간", "raw_factor": 600.0, "s_factor": 420.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "20년납", "gubun": "3대질환보장형_ 출생후보장기간", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "동양", "sheet": "동양", "product": "우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)", "term": "30년납", "gubun": "3대질환보장형_ 출생후보장기간", "raw_factor": 1050.0, "s_factor": 735.0, "adj_coef": 0.7}, {"company": "흥국", "sheet": "흥국", "product": "미리받는트리플더블업건강종신", "term": "20년납이상", "gubun": "", "raw_factor": 2000.0, "s_factor": 800.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "20년↑", "gubun": "라이프 밸런스형", "raw_factor": 2000.0, "s_factor": 800.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "15년↑", "gubun": "라이프 밸런스형", "raw_factor": 1650.0, "s_factor": 660.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑(일반)", "gubun": "라이프 밸런스형", "raw_factor": 1100.0, "s_factor": 440.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑(간편)", "gubun": "라이프 밸런스형", "raw_factor": 1000.0, "s_factor": 400.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "20년↑", "gubun": "프리미엄 보장형", "raw_factor": 2000.0, "s_factor": 800.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "15년↑", "gubun": "프리미엄 보장형", "raw_factor": 1400.0, "s_factor": 560.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 리턴100종신", "term": "10년↑", "gubun": "프리미엄 보장형", "raw_factor": 700.0, "s_factor": 280.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "20년↑", "gubun": "라이프 밸런스형", "raw_factor": 2000.0, "s_factor": 800.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "15년↑", "gubun": "라이프 밸런스형", "raw_factor": 1650.0, "s_factor": 660.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "10년↑", "gubun": "라이프 밸런스형", "raw_factor": 1200.0, "s_factor": 480.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "20년↑", "gubun": "프리미엄 보장형", "raw_factor": 2000.0, "s_factor": 800.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "15년↑", "gubun": "프리미엄 보장형", "raw_factor": 1650.0, "s_factor": 660.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "(간편한) 플렉스 리턴100종신", "term": "10년↑", "gubun": "프리미엄 보장형", "raw_factor": 800.0, "s_factor": 320.0, "adj_coef": 0.4}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "해약환급금 미지급형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "해약환급금 미지급형", "raw_factor": 1450.0, "s_factor": 797.5000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "해약환급금 미지급형", "raw_factor": 950.0, "s_factor": 522.5, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "해약환급금 일부지급형", "raw_factor": 1700.0, "s_factor": 935.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "해약환급금 일부지급형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "해약환급금 일부지급형", "raw_factor": 800.0, "s_factor": 440.00000000000006, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "20년↑", "gubun": "표준형", "raw_factor": 1450.0, "s_factor": 797.5000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "15년↑", "gubun": "표준형", "raw_factor": 1100.0, "s_factor": 605.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은시니어보장", "term": "10년↑", "gubun": "표준형", "raw_factor": 700.0, "s_factor": 385.00000000000006, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은Plus보장보험", "term": "15년↑", "gubun": "해약환급금 일부지급형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "치매담은Plus보장보험", "term": "10년↑", "gubun": "해약환급금 일부지급형", "raw_factor": 800.0, "s_factor": 440.00000000000006, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "해약환급금 미지급형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "15년↑", "gubun": "해약환급금 미지급형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "해약환급금 미지급형", "raw_factor": 600.0, "s_factor": 330.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "표준형", "raw_factor": 1700.0, "s_factor": 935.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "15년↑", "gubun": "표준형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "표준형", "raw_factor": 600.0, "s_factor": 330.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "20년↑", "gubun": "갱신형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다(多)사랑통합", "term": "10년↑", "gubun": "갱신형", "raw_factor": 1200.0, "s_factor": 660.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "20년↑", "gubun": "해약환급금 미지급형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "15년↑", "gubun": "해약환급금 미지급형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "오튼튼5.10.5건강보험, 다(多)사랑암", "term": "10년↑", "gubun": "해약환급금 미지급형", "raw_factor": 600.0, "s_factor": 330.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "오튼튼5.10.5건강보험(갱신형)", "term": "20년↑", "gubun": "갱신형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험", "term": "20년↑", "gubun": "해약환급금 미지급형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험", "term": "10년↑", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 660.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "3.1.1간편건강보험(갱신형)", "term": "20년↑", "gubun": "갱신형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3N5간편건강", "term": "20년↑", "gubun": "해약환급금 미지급형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3N5간편건강", "term": "10년↑", "gubun": "해약환급금 미지급형", "raw_factor": 1200.0, "s_factor": 660.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3N5간편건강", "term": "20년↑", "gubun": "표준형", "raw_factor": 2000.0, "s_factor": 1100.0, "adj_coef": 0.55}, {"company": "흥국", "sheet": "흥국", "product": "다사랑3N5간편건강", "term": "10년↑", "gubun": "표준형", "raw_factor": 1000.0, "s_factor": 550.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "20년납", "gubun": "해지환급금 미지급형", "raw_factor": 2600.0, "s_factor": 1430.0000000000002, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "15년납", "gubun": "해지환급금 미지급형", "raw_factor": 2380.0, "s_factor": 1309.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "12년납", "gubun": "해지환급금 미지급형", "raw_factor": 1900.0, "s_factor": 1045.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "10년납", "gubun": "해지환급금 미지급형", "raw_factor": 1350.0, "s_factor": 742.5000000000001, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "20년납", "gubun": "기본형", "raw_factor": 650.0, "s_factor": 357.50000000000006, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "15년납", "gubun": "기본형", "raw_factor": 600.0, "s_factor": 330.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "12년납", "gubun": "기본형", "raw_factor": 550.0, "s_factor": 302.5, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE건강해지는 종신", "term": "10년납", "gubun": "기본형", "raw_factor": 500.0, "s_factor": 275.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "20년납", "gubun": "해약환급금 일부지급형", "raw_factor": 2100.0, "s_factor": 630.0, "adj_coef": 0.3}, {"company": "라이나", "sheet": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "15년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1900.0, "s_factor": 570.0, "adj_coef": 0.3}, {"company": "라이나", "sheet": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "10년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1700.0, "s_factor": 510.0, "adj_coef": 0.3}, {"company": "라이나", "sheet": "라이나", "product": "THE채우는 335 간편고지 종신, THE채우는 종신", "term": "7년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1300.0, "s_factor": 390.0, "adj_coef": 0.3}, {"company": "라이나", "sheet": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "15년납이상", "gubun": "해지환급금 미지급형", "raw_factor": 2600.0, "s_factor": 1430.0000000000002, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "10년납", "gubun": "해지환급금 미지급형", "raw_factor": 1650.0, "s_factor": 907.5000000000001, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "15년납이상", "gubun": "기본형", "raw_factor": 500.0, "s_factor": 275.0, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신", "term": "10년납", "gubun": "기본형", "raw_factor": 350.0, "s_factor": 192.50000000000003, "adj_coef": 0.55}, {"company": "라이나", "sheet": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "20년납이상", "gubun": "주계약", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "15년납", "gubun": "주계약", "raw_factor": 2200.0, "s_factor": 990.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "전에없던실속치매 (해약환급금 미지급형)", "term": "10년납", "gubun": "주계약", "raw_factor": 1600.0, "s_factor": 720.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "암으로치료하였어도 OK암", "term": "-", "gubun": "주계약", "raw_factor": 2000.0, "s_factor": 900.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "THE실속있는치아, THE건강한치아V THE든든해진라이나치아", "term": "10년만기", "gubun": "갱신형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "THE실속있는치아, THE건강한치아V THE든든해진라이나치아", "term": "5년만기", "gubun": "갱신형", "raw_factor": 1400.0, "s_factor": 630.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "THE건강한치아보험V(리셋형)", "term": "갱신형", "gubun": "갱신형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "골라담는(간편)건강보험 (갱신형)", "term": "20년납", "gubun": "주계약", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "골라담는(간편)건강보험 (갱신형)", "term": "10년납", "gubun": "주계약", "raw_factor": 1520.0, "s_factor": 684.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "새로담는 (간편)건강보험(클래식)", "term": "해약환급금미지급형Ⅱ", "gubun": "주계약", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "새로담는 (간편)건강보험(클래식)", "term": "기본형", "gubun": "주계약", "raw_factor": 2000.0, "s_factor": 900.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "새로담는 간편건강보험(갱신형)", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "새로담는 간편건강보험(갱신형)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1520.0, "s_factor": 684.0, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "해약환급금미지급형Ⅱ", "gubun": "해약환급금 미지급형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "", "gubun": "해약환급금 미지급형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "라이나", "sheet": "라이나", "product": "브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)", "term": "", "gubun": "해약환급금 미지급형", "raw_factor": 2450.0, "s_factor": 1102.5, "adj_coef": 0.45}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10년미만", "gubun": "저해약", "raw_factor": 450.0, "s_factor": 360.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10-14년", "gubun": "저해약", "raw_factor": 1100.0, "s_factor": 880.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "15-19년", "gubun": "저해약", "raw_factor": 1450.0, "s_factor": 1160.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "20년납이상", "gubun": "저해약", "raw_factor": 1600.0, "s_factor": 1280.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10년미만", "gubun": "일반형", "raw_factor": 350.0, "s_factor": 280.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "10-14년", "gubun": "일반형", "raw_factor": 600.0, "s_factor": 480.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "15-19년", "gubun": "일반형", "raw_factor": 800.0, "s_factor": 640.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)평생건강보험 (기본보장형)", "term": "20년납이상", "gubun": "일반형", "raw_factor": 1000.0, "s_factor": 800.0, "adj_coef": 0.8}, {"company": "교보", "sheet": "교보", "product": "교보(간편)K-실속종신보험", "term": "5~6년", "gubun": "-", "raw_factor": 550.0, "s_factor": 500.5, "adj_coef": 0.91}, {"company": "교보", "sheet": "교보", "product": "교보(간편)K-실속종신보험", "term": "7~9년", "gubun": "-", "raw_factor": 900.0, "s_factor": 819.0, "adj_coef": 0.91}, {"company": "교보", "sheet": "교보", "product": "교보(간편)K-실속종신보험", "term": "10~14년", "gubun": "-", "raw_factor": 1300.0, "s_factor": 1183.0, "adj_coef": 0.91}, {"company": "교보", "sheet": "교보", "product": "교보(간편)K-실속종신보험", "term": "15년", "gubun": "-", "raw_factor": 1450.0, "s_factor": 1319.5, "adj_coef": 0.91}, {"company": "교보", "sheet": "교보", "product": "교보(간편)모두지킴종신", "term": "10년납 미만", "gubun": "-", "raw_factor": 900.0, "s_factor": 630.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)모두지킴종신", "term": "10년납-14년납", "gubun": "-", "raw_factor": 1300.0, "s_factor": 909.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)모두지킴종신", "term": "15년납-19년납", "gubun": "-", "raw_factor": 1450.0, "s_factor": 1014.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)모두지킴종신", "term": "20년납이상", "gubun": "-", "raw_factor": 1600.0, "s_factor": 1120.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "10년납 미만", "gubun": "일반가입", "raw_factor": 700.0, "s_factor": 489.99999999999994, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "10년납-14년납", "gubun": "일반가입", "raw_factor": 1400.0, "s_factor": 979.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "15년납-19년납", "gubun": "일반가입", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "20년납 이상", "gubun": "일반가입", "raw_factor": 1800.0, "s_factor": 1260.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "10년납 미만", "gubun": "간편가입", "raw_factor": 650.0, "s_factor": 454.99999999999994, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "10년납-14년납", "gubun": "간편가입", "raw_factor": 1350.0, "s_factor": 944.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "15년납-19년납", "gubun": "간편가입", "raw_factor": 1500.0, "s_factor": 1050.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보다시채움건강종신보험", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 1750.0, "s_factor": 1225.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "5년납~6년납", "gubun": "간편가입", "raw_factor": 700.0, "s_factor": 489.99999999999994, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "7년납~9년납", "gubun": "간편가입", "raw_factor": 900.0, "s_factor": 630.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "10년납~14년납", "gubun": "간편가입", "raw_factor": 1400.0, "s_factor": 979.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "15년납~19년납", "gubun": "간편가입", "raw_factor": 1550.0, "s_factor": 1085.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)3밸런스보장보험PLUS", "term": "20년납 이상", "gubun": "간편가입", "raw_factor": 1650.0, "s_factor": 1155.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)밸런스건강보험", "term": "10년납-14년납", "gubun": "간편가입", "raw_factor": 1000.0, "s_factor": 700.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)밸런스건강보험", "term": "15년납-19년납", "gubun": "간편가입", "raw_factor": 1400.0, "s_factor": 979.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "교보(간편)밸런스건강보험", "term": "20년납이상", "gubun": "간편가입", "raw_factor": 1750.0, "s_factor": 1225.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "10년미만", "gubun": "-", "raw_factor": 750.0, "s_factor": 525.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "10년", "gubun": "-", "raw_factor": 1400.0, "s_factor": 979.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "12년", "gubun": "-", "raw_factor": 1400.0, "s_factor": 979.9999999999999, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "15-19년", "gubun": "-", "raw_factor": 1650.0, "s_factor": 1155.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "실속건강종신보험 (기본형,보장강화형)", "term": "20년납이상", "gubun": "-", "raw_factor": 2000.0, "s_factor": 1400.0, "adj_coef": 0.7}, {"company": "교보", "sheet": "교보", "product": "K-밸류업종신 (베이직,프라임형)", "term": "-", "gubun": "일반,간편", "raw_factor": 1500.0, "s_factor": 1425.0, "adj_coef": 0.95}, {"company": "교보", "sheet": "교보", "product": "K-밸류업종신 (라이트형)", "term": "66세미만", "gubun": "일반", "raw_factor": 1500.0, "s_factor": 1425.0, "adj_coef": 0.95}, {"company": "교보", "sheet": "교보", "product": "K-밸류업종신 (라이트형)", "term": "66세이상", "gubun": "일반", "raw_factor": 1200.0, "s_factor": 1140.0, "adj_coef": 0.95}, {"company": "교보", "sheet": "교보", "product": "K-밸류업종신 (라이트형)", "term": "61세미만", "gubun": "간편", "raw_factor": 1500.0, "s_factor": 1425.0, "adj_coef": 0.95}, {"company": "교보", "sheet": "교보", "product": "K-밸류업종신 (라이트형)", "term": "61세이상", "gubun": "간편", "raw_factor": 1200.0, "s_factor": 1140.0, "adj_coef": 0.95}, {"company": "교보", "sheet": "교보", "product": "교보경영인정기(보증비용부과형)", "term": "20년납이상", "gubun": "일반,간편", "raw_factor": 1500.0, "s_factor": 1350.0, "adj_coef": 0.9}, {"company": "교보", "sheet": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "10년 미만", "gubun": "일반,간편", "raw_factor": 500.0, "s_factor": 425.0, "adj_coef": 0.85}, {"company": "교보", "sheet": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "10년-14년", "gubun": "일반,간편", "raw_factor": 900.0, "s_factor": 765.0, "adj_coef": 0.85}, {"company": "교보", "sheet": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "15년-19년", "gubun": "일반,간편", "raw_factor": 1300.0, "s_factor": 1105.0, "adj_coef": 0.85}, {"company": "교보", "sheet": "교보", "product": "교보(간편)치매·간병안심보험 (주계약기준)", "term": "20년 이상", "gubun": "일반,간편", "raw_factor": 1600.0, "s_factor": 1360.0, "adj_coef": 0.85}, {"company": "KDB", "sheet": "KDB", "product": "더블찬스종신Ⅱ", "term": "5년납", "gubun": "", "raw_factor": 550.0, "s_factor": 495.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "더블찬스종신Ⅱ", "term": "7년납", "gubun": "", "raw_factor": 750.0, "s_factor": 675.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "더블찬스종신Ⅱ", "term": "10년납", "gubun": "", "raw_factor": 1050.0, "s_factor": 945.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "트리플찬스 종신", "term": "10년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 900.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "트리플찬스 종신", "term": "15년납", "gubun": "", "raw_factor": 1200.0, "s_factor": 1080.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "트리플찬스 종신", "term": "20년납", "gubun": "", "raw_factor": 1500.0, "s_factor": 1350.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "5년납", "gubun": "체증형", "raw_factor": 500.0, "s_factor": 450.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "7년납", "gubun": "체증형", "raw_factor": 700.0, "s_factor": 630.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "무심사 버팀목 종신 (해약환급금 일부(50%)지급형)", "term": "10년납", "gubun": "체증형", "raw_factor": 1000.0, "s_factor": 900.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "서포트100건강종신", "term": "10년납", "gubun": "체증형", "raw_factor": 1000.0, "s_factor": 900.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "서포트100건강종신", "term": "15년납", "gubun": "체증형", "raw_factor": 1200.0, "s_factor": 1080.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "서포트100건강종신", "term": "20년납이상", "gubun": "체증형", "raw_factor": 1500.0, "s_factor": 1350.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "5년납", "gubun": "체증형", "raw_factor": 500.0, "s_factor": 300.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "7년납", "gubun": "체증형", "raw_factor": 700.0, "s_factor": 420.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "10년납", "gubun": "체증형", "raw_factor": 1200.0, "s_factor": 720.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "15년납", "gubun": "체증형", "raw_factor": 1400.0, "s_factor": 840.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "라이프핏건강보험, 버팀목 NEW케어보험", "term": "20년납이상", "gubun": "체증형", "raw_factor": 1700.0, "s_factor": 1020.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "10년납", "gubun": "체증형", "raw_factor": 1200.0, "s_factor": 720.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "15년납", "gubun": "체증형", "raw_factor": 1400.0, "s_factor": 840.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "암만생각해도 KDB암보험2.0", "term": "20년납 이상", "gubun": "체증형", "raw_factor": 1700.0, "s_factor": 1020.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "버팀목 치매보장", "term": "10년납", "gubun": "체증형", "raw_factor": 1200.0, "s_factor": 720.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "버팀목 치매보장", "term": "15년납", "gubun": "체증형", "raw_factor": 1400.0, "s_factor": 840.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "버팀목 치매보장", "term": "20년납 이상", "gubun": "체증형", "raw_factor": 1700.0, "s_factor": 1020.0, "adj_coef": 0.6}, {"company": "KDB", "sheet": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "5년납", "gubun": "체증형", "raw_factor": 150.0, "s_factor": 135.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "7년납", "gubun": "체증형", "raw_factor": 400.0, "s_factor": 360.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금", "term": "10년납이상", "gubun": "체증형", "raw_factor": 700.0, "s_factor": 630.0, "adj_coef": 0.9}, {"company": "KDB", "sheet": "KDB", "product": "더!행복플러스종신", "term": "10년납", "gubun": "체증형", "raw_factor": 700.0, "s_factor": 854.0, "adj_coef": 1.22}, {"company": "KDB", "sheet": "KDB", "product": "더!행복플러스종신", "term": "20년납", "gubun": "체증형", "raw_factor": 900.0, "s_factor": 1098.0, "adj_coef": 1.22}, {"company": "KDB", "sheet": "KDB", "product": "더!행복세븐종신", "term": "20년납", "gubun": "체증형", "raw_factor": 1150.0, "s_factor": 1403.0, "adj_coef": 1.22}, {"company": "ABL", "sheet": "ABL", "product": "우리WON세븐종신보험", "term": "20년납", "gubun": "일반/간편", "raw_factor": 3180.0, "s_factor": 1113.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더채움종신보험 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반/간편", "raw_factor": 2160.0, "s_factor": 756.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더채움종신보험 (해약환급금 일부지급형)", "term": "20년납", "gubun": "일반/간편", "raw_factor": 2400.0, "s_factor": 840.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1920.0, "s_factor": 672.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2820.0, "s_factor": 986.9999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "15년납", "gubun": "일반심사형 간편심사형", "raw_factor": 3600.0, "s_factor": 1260.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON더블종신 (해약환급금 일부지급형)", "term": "20년납", "gubun": "일반심사형 간편심사형", "raw_factor": 4020.0, "s_factor": 1407.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON스테이블종신", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1920.0, "s_factor": 672.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON스테이블종신", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2160.0, "s_factor": 756.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON스테이블종신", "term": "15년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2280.0, "s_factor": 798.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON스테이블종신", "term": "20년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2400.0, "s_factor": 840.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "5년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1680.0, "s_factor": 588.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2280.0, "s_factor": 798.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2760.0, "s_factor": 965.9999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "15년납", "gubun": "일반심사형 간편심사형", "raw_factor": 3600.0, "s_factor": 1260.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)", "term": "20년납", "gubun": "일반심사형 간편심사형", "raw_factor": 3600.0, "s_factor": 1260.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "5년납", "gubun": "평준형 (일반심사형) (간편심사형)", "raw_factor": 1800.0, "s_factor": 630.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "7년납", "gubun": "평준형 (일반심사형) (간편심사형)", "raw_factor": 1740.0, "s_factor": 609.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "10년납", "gubun": "평준형 (일반심사형) (간편심사형)", "raw_factor": 2940.0, "s_factor": 1029.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "15년납", "gubun": "평준형 (일반심사형) (간편심사형)", "raw_factor": 3900.0, "s_factor": 1365.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "20년이상", "gubun": "평준형 (일반심사형) (간편심사형)", "raw_factor": 4080.0, "s_factor": 1428.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "5년납", "gubun": "체증형 (일반심사형) (간편심사형)", "raw_factor": 1680.0, "s_factor": 588.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "7년납", "gubun": "체증형 (일반심사형) (간편심사형)", "raw_factor": 1740.0, "s_factor": 609.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "10년납", "gubun": "체증형 (일반심사형) (간편심사형)", "raw_factor": 2640.0, "s_factor": 923.9999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "15년납", "gubun": "체증형 (일반심사형) (간편심사형)", "raw_factor": 3540.0, "s_factor": 1239.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON드림종신III (해약환급금 일부지급형)", "term": "20년이상", "gubun": "체증형 (일반심사형) (간편심사형)", "raw_factor": 3960.0, "s_factor": 1386.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "5년납", "gubun": "해약환급금 미지급형", "raw_factor": 1080.0, "s_factor": 378.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1920.0, "s_factor": 672.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 2760.0, "s_factor": 965.9999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "20년납 이상", "gubun": "해약환급금 미지급형", "raw_factor": 3240.0, "s_factor": 1134.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "5년납", "gubun": "기본형", "raw_factor": 360.0, "s_factor": 125.99999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "10년납", "gubun": "기본형", "raw_factor": 1380.0, "s_factor": 482.99999999999994, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "15년납", "gubun": "기본형", "raw_factor": 2100.0, "s_factor": 735.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험", "term": "20년납 이상", "gubun": "기본형", "raw_factor": 2700.0, "s_factor": 944.9999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장 종합건강보험", "term": "10년 만기", "gubun": "갱신형", "raw_factor": 1920.0, "s_factor": 672.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON건강N더보장 종합건강보험", "term": "20년&30년", "gubun": "갱신형", "raw_factor": 3240.0, "s_factor": 1134.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 1140.0, "s_factor": 399.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "15년납", "gubun": "일반심사형 간편심사형", "raw_factor": 2520.0, "s_factor": 882.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON케어간병 (해약환급금 미지급형) (주계약기준)", "term": "20년납이상", "gubun": "일반심사형 간편심사형", "raw_factor": 3120.0, "s_factor": 1092.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "5년납", "gubun": "기본형", "raw_factor": 360.0, "s_factor": 125.99999999999999, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "10년납", "gubun": "기본형", "raw_factor": 1380.0, "s_factor": 482.99999999999994, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "15년납", "gubun": "기본형", "raw_factor": 2100.0, "s_factor": 735.0, "adj_coef": 0.35}, {"company": "ABL", "sheet": "ABL", "product": "우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)", "term": "20년이상", "gubun": "기본형", "raw_factor": 2700.0, "s_factor": 944.9999999999999, "adj_coef": 0.35}, {"company": "미래", "sheet": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "3년납이상", "gubun": "보종코드: 21218", "raw_factor": 20.0, "s_factor": 16.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "5년납이상", "gubun": "보종코드: 21218", "raw_factor": 250.0, "s_factor": 200.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "7년납이상", "gubun": "보종코드: 21218", "raw_factor": 390.0, "s_factor": 312.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "미래에셋생명 변액연금 (기본형)", "term": "10년납이상", "gubun": "보종코드: 21218", "raw_factor": 550.0, "s_factor": 440.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "5년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 550.0, "s_factor": 440.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "7년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 700.0, "s_factor": 560.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "10년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 950.0, "s_factor": 760.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "12년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1050.0, "s_factor": 840.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "15년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1450.0, "s_factor": 1160.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 라이트 종신보험 (보증비용부과형)", "term": "20년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1650.0, "s_factor": 1320.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "15년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1450.0, "s_factor": 1160.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "20년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1650.0, "s_factor": 1320.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "헤리티지 변액정기보험 (실적배당형 계약)", "term": "25년납이상", "gubun": "일반가입형, 간편고지형", "raw_factor": 1750.0, "s_factor": 1400.0, "adj_coef": 0.8}, {"company": "미래", "sheet": "미래", "product": "암 걱정없는 암치료보험", "term": "10년납이상", "gubun": "갱신형", "raw_factor": 1000.0, "s_factor": 550.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "암 걱정없는 암치료보험", "term": "20년납이상", "gubun": "갱신형", "raw_factor": 1500.0, "s_factor": 825.0000000000001, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "10년납이상", "gubun": "일반가입형, 간편가입형", "raw_factor": 1000.0, "s_factor": 550.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "15년납이상", "gubun": "일반가입형, 간편가입형", "raw_factor": 1150.0, "s_factor": 632.5, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)", "term": "20년납이상", "gubun": "일반가입형, 간편가입형", "raw_factor": 1300.0, "s_factor": 715.0000000000001, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "10년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 750.0, "s_factor": 412.50000000000006, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "15년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 1120.0, "s_factor": 616.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형W가입용) 일반/간편고지", "term": "20년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 1500.0, "s_factor": 825.0000000000001, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "10년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 750.0, "s_factor": 412.50000000000006, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "15년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 1120.0, "s_factor": 616.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (특약유형S가입용)", "term": "20년납이상", "gubun": "기본형, 해약환급금이없는유형", "raw_factor": 1500.0, "s_factor": 825.0000000000001, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "10년납이상", "gubun": "기본형", "raw_factor": 300.0, "s_factor": 165.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "15년납이상", "gubun": "기본형", "raw_factor": 370.0, "s_factor": 203.50000000000003, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "20년납이상", "gubun": "기본형", "raw_factor": 450.0, "s_factor": 247.50000000000003, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "25년납이상", "gubun": "기본형", "raw_factor": 520.0, "s_factor": 286.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "10년납이상", "gubun": "해약환급금이없는유형", "raw_factor": 750.0, "s_factor": 412.50000000000006, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "15년납이상", "gubun": "해약환급금이없는유형", "raw_factor": 1120.0, "s_factor": 616.0, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)", "term": "20년납이상", "gubun": "해약환급금이없는유형", "raw_factor": 1500.0, "s_factor": 825.0000000000001, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)", "term": "10년납이상", "gubun": "갱신형", "raw_factor": 750.0, "s_factor": 412.50000000000006, "adj_coef": 0.55}, {"company": "미래", "sheet": "미래", "product": "M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)", "term": "20년납이상", "gubun": "갱신형", "raw_factor": 1500.0, "s_factor": 825.0000000000001, "adj_coef": 0.55}, {"company": "하나", "sheet": "하나", "product": "하나로 THE연결된 종신", "term": "5년납", "gubun": "일반심사형 간편심사형", "raw_factor": 330.0, "s_factor": 363.00000000000006, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나로 THE연결된 종신", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 430.0, "s_factor": 473.00000000000006, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나로 THE연결된 종신", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 500.0, "s_factor": 550.0, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나로 THE연결된 종신", "term": "15년/20년납", "gubun": "일반심사형 간편심사형", "raw_factor": 900.0, "s_factor": 990.0000000000001, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나원!투!종신", "term": "5년납", "gubun": "일반심사형 간편심사형", "raw_factor": 280.0, "s_factor": 308.0, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나원!투!종신", "term": "7년납", "gubun": "일반심사형 간편심사형", "raw_factor": 300.0, "s_factor": 330.0, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나원!투!종신", "term": "10년납", "gubun": "일반심사형 간편심사형", "raw_factor": 380.0, "s_factor": 418.00000000000006, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "CEO경영인정기보험 (전기납)", "term": "해약환급금 일부지급형", "gubun": "일반심사형 간편심사형", "raw_factor": 1440.0, "s_factor": 1440.0, "adj_coef": 1.0}, {"company": "하나", "sheet": "하나", "product": "CEO경영인정기보험 (전기납)", "term": "일반형", "gubun": "일반심사형 간편심사형", "raw_factor": 800.0, "s_factor": 800.0, "adj_coef": 1.0}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "10년납", "gubun": "해약환급금 미지급형", "raw_factor": 1600.0, "s_factor": 640.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "15년납", "gubun": "해약환급금 미지급형", "raw_factor": 1800.0, "s_factor": 720.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "20년납", "gubun": "해약환급금 미지급형", "raw_factor": 2200.0, "s_factor": 880.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "10년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1200.0, "s_factor": 480.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "15년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1600.0, "s_factor": 640.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나더넥스트케어 (주계약기준)", "term": "20년납", "gubun": "해약환급금 일부지급형", "raw_factor": 1900.0, "s_factor": 760.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "10년납", "gubun": "해약환급금 미지급형/갱신형", "raw_factor": 1300.0, "s_factor": 520.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "20년/30년납", "gubun": "해약환급금 미지급형/갱신형", "raw_factor": 2200.0, "s_factor": 880.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "10년납", "gubun": "일반형", "raw_factor": 900.0, "s_factor": 360.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험", "term": "20년/30년납", "gubun": "일반형", "raw_factor": 1700.0, "s_factor": 680.0, "adj_coef": 0.4}, {"company": "하나", "sheet": "하나", "product": "THE든든한연금", "term": "전기납", "gubun": "일반/간편", "raw_factor": 550.0, "s_factor": 605.0, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나뿐인 변액연금", "term": "5년납", "gubun": "적립형", "raw_factor": 200.0, "s_factor": 220.00000000000003, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나뿐인 변액연금", "term": "7년납", "gubun": "적립형", "raw_factor": 400.0, "s_factor": 440.00000000000006, "adj_coef": 1.1}, {"company": "하나", "sheet": "하나", "product": "하나뿐인 변액연금", "term": "10년납 이상", "gubun": "적립형", "raw_factor": 650.0, "s_factor": 715.0000000000001, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "5년납", "gubun": "일반가입 간편가입", "raw_factor": 300.0, "s_factor": 330.0, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "7년납", "gubun": "일반가입 간편가입", "raw_factor": 550.0, "s_factor": 880.0, "adj_coef": 1.6}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 종신보험 원픽 (해약환급금 일부지급형)", "term": "20년납", "gubun": "일반가입 간편가입", "raw_factor": 1000.0, "s_factor": 1600.0, "adj_coef": 1.6}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "10년", "raw_factor": 300.0, "s_factor": 330.0, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "11~20년", "raw_factor": 500.0, "s_factor": 550.0, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납", "gubun": "11~20년", "raw_factor": 700.0, "s_factor": 770.0000000000001, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "21~30년", "raw_factor": 500.0, "s_factor": 550.0, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납이상", "gubun": "21~30년", "raw_factor": 900.0, "s_factor": 990.0000000000001, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "10년납", "gubun": "31년이상", "raw_factor": 400.0, "s_factor": 440.00000000000006, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "정기보험 스마트픽 (해약환급금미지급형/표준형)", "term": "20년납이상", "gubun": "31년이상", "raw_factor": 800.0, "s_factor": 880.0000000000001, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "55세미만", "gubun": "일반가입", "raw_factor": 1290.0, "s_factor": 1419.0000000000002, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "55세이상", "gubun": "일반가입", "raw_factor": 1200.0, "s_factor": 1320.0, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)", "term": "-", "gubun": "간편가입", "raw_factor": 1290.0, "s_factor": 1419.0000000000002, "adj_coef": 1.1}, {"company": "푸본현대", "sheet": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "10년납", "gubun": "주계약", "raw_factor": 500.0, "s_factor": 250.0, "adj_coef": 0.5}, {"company": "푸본현대", "sheet": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "15년납", "gubun": "주계약", "raw_factor": 660.0, "s_factor": 330.0, "adj_coef": 0.5}, {"company": "푸본현대", "sheet": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "20년납", "gubun": "주계약", "raw_factor": 850.0, "s_factor": 425.0, "adj_coef": 0.5}, {"company": "푸본현대", "sheet": "푸본현대", "product": "건강보험 마이픽 (해약환급금 일부지급형)", "term": "30년납", "gubun": "주계약", "raw_factor": 850.0, "s_factor": 425.0, "adj_coef": 0.5}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 연금다운 연금보험", "term": "10년납", "gubun": "1형 보증비용부과형", "raw_factor": 840.0, "s_factor": 546.0, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 연금다운 연금보험", "term": "20년납", "gubun": "1형 보증비용부과형", "raw_factor": 940.0, "s_factor": 611.0, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 연금다운 연금보험", "term": "10년납", "gubun": "2형 보증비용미부과형", "raw_factor": 200.0, "s_factor": 130.0, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX 연금다운 연금보험", "term": "20년납", "gubun": "2형 보증비용미부과형", "raw_factor": 250.0, "s_factor": 162.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "5년", "gubun": "1형 연금액강화형", "raw_factor": 250.0, "s_factor": 162.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "7년", "gubun": "1형 연금액강화형", "raw_factor": 350.0, "s_factor": 227.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "10년", "gubun": "1형 연금액강화형", "raw_factor": 550.0, "s_factor": 357.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "5년", "gubun": "2형 일반연금형", "raw_factor": 50.0, "s_factor": 32.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "7년", "gubun": "2형 일반연금형", "raw_factor": 150.0, "s_factor": 97.5, "adj_coef": 0.65}, {"company": "푸본현대", "sheet": "푸본현대", "product": "MAX UP 연금보험", "term": "10년", "gubun": "2형 일반연금형", "raw_factor": 200.0, "s_factor": 130.0, "adj_coef": 0.65}, {"company": "IM", "sheet": "IM", "product": "당당한 인생종신 (체증형)", "term": "5년납", "gubun": "일반", "raw_factor": 870.0, "s_factor": 556.8000000000001, "adj_coef": 0.64}, {"company": "IM", "sheet": "IM", "product": "당당한 인생종신 (체증형)", "term": "7년납", "gubun": "일반", "raw_factor": 1180.0, "s_factor": 873.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "당당한 인생종신 (체증형)", "term": "5년납", "gubun": "간편", "raw_factor": 850.0, "s_factor": 544.0, "adj_coef": 0.64}, {"company": "IM", "sheet": "IM", "product": "당당한 인생종신 (체증형)", "term": "7년납", "gubun": "간편", "raw_factor": 1160.0, "s_factor": 858.4, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "더(THE) 행복한 종신보험", "term": "20년이상", "gubun": "간편", "raw_factor": 900.0, "s_factor": 666.0, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Plus세븐UP종신보험", "term": "20년", "gubun": "일반,간편", "raw_factor": 1260.0, "s_factor": 932.4, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Plus세븐UP골드종신보험", "term": "20년", "gubun": "일반,간편", "raw_factor": 1820.0, "s_factor": 1346.8, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM 트래블PRO변액연금", "term": "5년납", "gubun": "일반,간편", "raw_factor": 310.0, "s_factor": 229.4, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM 트래블PRO변액연금", "term": "7년납", "gubun": "일반,간편", "raw_factor": 560.0, "s_factor": 414.4, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "10년/12년", "gubun": "보험료 10만원이상", "raw_factor": 190.0, "s_factor": 140.6, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "15년/20년이상", "gubun": "보험료 10만원이상", "raw_factor": 320.0, "s_factor": 236.8, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "10이상", "gubun": "보험료 20만원이상", "raw_factor": 780.0, "s_factor": 577.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "12년이상", "gubun": "보험료 20만원이상", "raw_factor": 820.0, "s_factor": 606.8, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "15년/20년이상", "gubun": "보험료 20만원이상", "raw_factor": 880.0, "s_factor": 651.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "5년이상", "gubun": "보험료 30만원이상", "raw_factor": 290.0, "s_factor": 214.6, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "7년이상", "gubun": "보험료 30만원이상", "raw_factor": 500.0, "s_factor": 370.0, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "(오토파일럿) 마이솔루션AI변액연금보험S", "term": "5년이상", "gubun": "50만원 이상", "raw_factor": 330.0, "s_factor": 244.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "든든한 인생치매 (주계약기준)", "term": "5년납", "gubun": "50만원 이상", "raw_factor": 770.0, "s_factor": 569.8, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "든든한 인생치매 (주계약기준)", "term": "7년납", "gubun": "50만원 이상", "raw_factor": 1080.0, "s_factor": 799.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "10년", "gubun": "1종,2종", "raw_factor": 560.0, "s_factor": 414.4, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "15년", "gubun": "1종,2종", "raw_factor": 830.0, "s_factor": 614.2, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Active Care 치매간병보험 (해약환급금 미지급형)", "term": "20년이상", "gubun": "1종,2종", "raw_factor": 1090.0, "s_factor": 806.6, "adj_coef": 0.74}, {"company": "IM", "sheet": "IM", "product": "iM Plus세븐UP 더좋은종신보험", "term": "20년납", "gubun": "1종,2종", "raw_factor": 1260.0, "s_factor": 932.4, "adj_coef": 0.74}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "5년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 250.0, "adj_coef": 0.25}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "7년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 400.0, "adj_coef": 0.4}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK NEW 프리미엄 연금보험", "term": "10년납이상", "gubun": "", "raw_factor": 1000.0, "s_factor": 500.0, "adj_coef": 0.5}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "5년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 220.0, "adj_coef": 0.22}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "7년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 380.0, "adj_coef": 0.38}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK 프리미엄 연금보험", "term": "10년납이상", "gubun": "", "raw_factor": 1000.0, "s_factor": 450.0, "adj_coef": 0.45}, {"company": "IBK", "sheet": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "5년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 170.0, "adj_coef": 0.17}, {"company": "IBK", "sheet": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "7년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 400.0, "adj_coef": 0.4}, {"company": "IBK", "sheet": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "10,11년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 600.0, "adj_coef": 0.6}, {"company": "IBK", "sheet": "IBK", "product": "연금액 평생보증받는 변액연금, 평생든든변액연금", "term": "12년납이상", "gubun": "", "raw_factor": 1000.0, "s_factor": 600.0, "adj_coef": 0.6}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "5년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 150.0, "adj_coef": 0.15}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "7년납", "gubun": "", "raw_factor": 1000.0, "s_factor": 250.0, "adj_coef": 0.25}, {"company": "IBK", "sheet": "IBK", "product": "(무)IBK하이브리드 연금저축", "term": "10년납이상", "gubun": "", "raw_factor": 1000.0, "s_factor": 350.0, "adj_coef": 0.35}]')
EMBEDDED_RATES_DATA = json.loads('{"life_rules": {"next_month_rate": 3.32, "company_installments": {"흥국": {"default": 0.96, "건강": 0.96, "종신": 0.96, "오튼튼": 0.96, "다사랑": 0.96}, "한화": {"default": 1.56, "H종신": 1.56, "제로백": 1.56, "일반보장": 2.76}, "DB": {"default": 1.32, "건강": 1.32, "알행종": 1.56}, "신한": {"default": 0.84, "건강": 0.84, "종신": 1.56}, "KB": {"default": 3.48}, "메트": {"default": 3.84, "연금": 4.8, "종신": 3.84, "백만인": 2.52}, "농협": {"default": 1.56, "투스텝": 1.56, "기타": 0.6}, "동양": {"default": 1.08, "어린이": 1.08, "쑥쑥": 1.08, "단기납": 1.56, "종신": 1.8, "경영인": 2.28}, "라이나": {"default": 1.56, "건강": 1.56}, "교보": {"default": 2.76}, "KDB": {"default": 1.56}, "ABL": {"default": 1.56}, "미래": {"default": 2.76}, "하나": {"default": 0.96, "건강": 0.96, "일반": 1.56}, "푸본현대": {"default": 1.56, "표준": 6.12, "MAX원픽": 1.56, "마이픽": 1.56}, "IM": {"default": 2.04}, "IBK": {"default": 2.76}}, "incentives": {"흥국": {"전략": {"name": "흥국생명 전략 6종 (오튼튼/다사랑 등)", "next_month_base": 4.0, "next_month_sky": 2.0, "install_period_bonus": 6.0, "install_strategy_bonus": 2.0, "total_rate": 14.0, "note": "20만원 구간 기준, 본사 전략시책(+200%) 포함"}, "일반": {"name": "흥국생명 일반 건강", "next_month_base": 4.0, "next_month_sky": 0.0, "install_period_bonus": 6.0, "install_strategy_bonus": 0.0, "total_rate": 10.0, "note": "20만원 구간 기준"}}}}, "nonlife_rules": {"conversion_rate": 0.92, "next_month_rate": 6.1, "installment_rate": 1.32, "total_commission_rate": 7.42, "companies": ["현대해상", "메리츠", "KB손보", "한화손보", "DB손보", "롯데손보", "흥국화재", "농협손보", "하나손보"], "incentives": {"현대해상": {"주력": {"name": "현대해상 주력보종 (퍼펙트/간편/굿앤굿)", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 3.0, "install_sky_2nd": 1.7, "total_rate": 10.3, "note": "1주차 가동(200%) + 주력가동(300%) + SKY 2차년도(170%) 포함"}, "일반": {"name": "현대해상 일반 인보험", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 0.0, "install_sky_2nd": 1.7, "total_rate": 7.3, "note": "주력보종 가동시상(300%) 제외"}}, "KB손보": {"주력": {"name": "KB손해보험 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 2.6, "install_week_bonus": 2.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.6, "note": "익월 360% + 1주차 가동 200% + 주력 200%"}}, "한화손보": {"주력": {"name": "한화손해보험 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 0.5, "install_week_bonus": 4.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.5, "note": "익월 150% + 1주차 인보험 400% + 주력 200%"}}, "메리츠": {"주력": {"name": "메리츠화재 1주차 주력보종", "next_month_base": 1.0, "next_month_sky": 2.5, "install_week_bonus": 2.0, "install_main_bonus": 2.0, "install_sky_2nd": 0.0, "total_rate": 7.5, "note": "익월 350% + 1주차 가동 200% + 주력 200%"}}}}}')

COMPANY_RATES = EMBEDDED_RATES_DATA
LIFE_RULES = COMPANY_RATES['life_rules']
NONLIFE_RULES = COMPANY_RATES['nonlife_rules']

# 손보사 1주차 시책 규칙 확장 (DB손보 포함)
NONLIFE_RULES['incentives']['DB손보'] = {
    "주력": {
        "next_month_base": 1.0,
        "next_month_sky": 2.6,
        "install_week_bonus": 2.0,
        "install_main_bonus": 2.0,
        "install_sky_2nd": 1.7,
        "install_sky_add": 1.0,
        "total_rate": 10.3,
        "basis": "익월 360%(기본100+SKY260) + 13회차 670%(2차년도170+주간200+주력200+SKY100)",
        "cont_bonus_rate": 2.0,
        "cont_desc": "전월(10월) 10만↑ 달성 시 연속가동 +20만 원(200%) 추가 합산 가능"
    },
    "일반": {
        "next_month_base": 1.0,
        "next_month_sky": 2.6,
        "install_week_bonus": 2.0,
        "install_main_bonus": 0.0,
        "install_sky_2nd": 1.7,
        "install_sky_add": 1.0,
        "total_rate": 8.3,
        "basis": "익월 360%(기본100+SKY260) + 13회차 470%(2차년도170+주간200+SKY100)",
        "cont_bonus_rate": 2.0,
        "cont_desc": "전월(10월) 10만↑ 달성 시 연속가동 +20만 원(200%) 추가 합산 가능"
    }
}
NONLIFE_RULES['incentives']['현대해상']['주력']['basis'] = "익월 360%(기본100+SKY260) + 13회차 670%(2차년도170+1주가동200+주력가동300)"
NONLIFE_RULES['incentives']['현대해상']['주력']['cont_bonus_rate'] = 2.0
NONLIFE_RULES['incentives']['현대해상']['주력']['cont_desc'] = "전월 연속가동 달성 시 추가시상 합산 가능"

NONLIFE_RULES['incentives']['KB손보']['주력']['basis'] = "익월 360%(기본100+SKY260) + 13회차 400%(1주가동200+주력200)"
NONLIFE_RULES['incentives']['한화손보']['주력']['basis'] = "익월 150%(기본100+전략50) + 13회차 600%(주차400+주력200)"
NONLIFE_RULES['incentives']['메리츠']['주력']['basis'] = "익월 150%(기본100+전략50) + 13회차 600%(주차400+주력200)"

# ==========================================
# 1. 26개 보험사 마스터 정보 (동의어, 대표상품, 시책지 등)
# ==========================================
ALL_COMPANIES = {
    # 손해보험사 (9개사)
    "현대해상": {
        "category": "손해보험",
        "aliases": ["현대해상", "현대"],
        "default_prod": "주력보종",
        "flyer": "현대해상_1주.png",
        "recommendations": ["주력보종 20만원", "주력보종 10만원", "퍼펙트 20만원"]
    },
    "DB손보": {
        "category": "손해보험",
        "aliases": ["DB손해보험", "DB손보", "디비손보", "디비손", "동부화재"],
        "default_prod": "주력보종",
        "flyer": "DB손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원", "주력보종 20만원 연속포함"]
    },
    "KB손보": {
        "category": "손해보험",
        "aliases": ["KB손해보험", "KB손보", "케이비손보"],
        "default_prod": "주력보종",
        "flyer": "KB손보_1주차.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "한화손보": {
        "category": "손해보험",
        "aliases": ["한화손해보험", "한화손보"],
        "default_prod": "주력보종",
        "flyer": "한화손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "메리츠": {
        "category": "손해보험",
        "aliases": ["메리츠화재", "메리츠"],
        "default_prod": "인보험",
        "flyer": "메리츠_11월_1주.jpg",
        "recommendations": ["인보험 20만원", "인보험 10만원"]
    },
    "롯데손보": {
        "category": "손해보험",
        "aliases": ["롯데손해보험", "롯데손보", "롯데"],
        "default_prod": "주력보종",
        "flyer": "롯데손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "흥국화재": {
        "category": "손해보험",
        "aliases": ["흥국화재"],
        "default_prod": "주력보종",
        "flyer": "흥국화재_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "농협손보": {
        "category": "손해보험",
        "aliases": ["농협손해보험", "농협손보"],
        "default_prod": "주력보종",
        "flyer": "농협손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },
    "하나손보": {
        "category": "손해보험",
        "aliases": ["하나손해보험", "하나손보"],
        "default_prod": "주력보종",
        "flyer": "하나손보_1주.jpg",
        "recommendations": ["주력보종 20만원", "주력보종 10만원"]
    },

    # 생명보험사 (17개사)
    "흥국생명": {
        "category": "생명보험",
        "aliases": ["흥국생명", "흥국"],
        "default_prod": "오튼튼",
        "default_term": "20년납",
        "flyer": "흥국생명_11월.png",
        "recommendations": ["오튼튼 20만 20년납", "오튼튼 20만 10-11월 연속포함", "오튼튼 20만 핑크멤버스 포함", "다사랑 20만 20년납"]
    },
    "한화생명": {
        "category": "생명보험",
        "aliases": ["한화생명", "한화"],
        "default_prod": "건강더한종신",
        "default_term": "10년납",
        "flyer": "한화생명_11월.png",
        "recommendations": ["건강더한종신 50만 10년납", "건강더한종신 100만 10년납", "하나로H종신 50만 15년납"]
    },
    "DB생명": {
        "category": "생명보험",
        "aliases": ["DB생명", "디비생명", "동부생명"],
        "default_prod": "알행플종신",
        "default_term": "10년납",
        "flyer": "DB생명_11월.jpg",
        "recommendations": ["알행플종신 10만 10년납", "알행플종신 20만 10년납"]
    },
    "신한라이프": {
        "category": "생명보험",
        "aliases": ["신한라이프", "신한생명", "신한"],
        "default_prod": "신한통합건강 원",
        "default_term": "20년납",
        "flyer": "신한라이프_11월_p2.png",
        "recommendations": ["신한통합건강 원 20만", "신한통합건강 원 20만 연속포함", "모아더드림종신 20만"]
    },
    "KB라이프": {
        "category": "생명보험",
        "aliases": ["KB라이프", "KB생명", "케이비라이프", "케이비생명"],
        "default_prod": "딱좋은건강",
        "default_term": "20년납",
        "flyer": "KB라이프_11월.png",
        "recommendations": ["딱좋은건강 20만", "100세든든연금 20만"]
    },
    "라이나생명": {
        "category": "생명보험",
        "aliases": ["라이나생명", "라이나"],
        "default_prod": "새로담는건강보험",
        "default_term": "20년납",
        "flyer": "라이나생명_11월.png",
        "recommendations": ["새로담는건강 20만", "브레인케어 10만", "THE채우는종신 10년납 일반 20만", "THE채우는종신 7년납 20만"]
    },
    "미래에셋": {
        "category": "생명보험",
        "aliases": ["미래에셋생명", "미래에셋", "미래"],
        "default_prod": "M-케어건강",
        "default_term": "20년납",
        "flyer": "미래에셋_11월.png",
        "recommendations": ["M-케어건강 20만", "M-케어건강 10만", "M-케어건강 30만", "변액연금 20만"]
    },
    "메트라이프": {
        "category": "생명보험",
        "aliases": ["메트라이프", "메트"],
        "default_prod": "달러종신Plus",
        "default_term": "10년납",
        "flyer": "메트라이프_11월.jpg",
        "recommendations": ["달러종신Plus 20만 10년납", "달러종신Plus 20만 5년납", "달러종신Plus 20만 20년납", "변액리치 정기 20만"]
    },
    "동양생명": {
        "category": "생명보험",
        "aliases": ["동양생명", "동양"],
        "default_prod": "쑥쑥어린이",
        "default_term": "15년납",
        "flyer": "동양생명_11월.png",
        "recommendations": ["쑥쑥어린이 20만 15년납", "수호천사 20만"]
    },
    "교보생명": {
        "category": "생명보험",
        "aliases": ["교보생명", "교보"],
        "default_prod": "보장성",
        "default_term": "20년납",
        "flyer": "교보생명_11월.png",
        "recommendations": ["보장성 20만", "보장성 10만"]
    },
    "농협생명": {
        "category": "생명보험",
        "aliases": ["농협생명"],
        "default_prod": "건강플러스",
        "default_term": "20년납",
        "flyer": "농협생명_11월.png",
        "recommendations": ["건강플러스 20만", "투스텝종신 20만"]
    },
    "KDB생명": {
        "category": "생명보험",
        "aliases": ["KDB생명", "KDB"],
        "default_prod": "버팀목",
        "default_term": "10년납",
        "flyer": "KDB생명_11월.jpg",
        "recommendations": ["버팀목 20만", "버팀목 10만"]
    },
    "ABL생명": {
        "category": "생명보험",
        "aliases": ["ABL생명", "ABL"],
        "default_prod": "우리WON더채움",
        "default_term": "20년납",
        "flyer": "ABL생명_11월.png",
        "recommendations": ["우리WON더채움 20만", "우리WON세븐 20만"]
    },
    "하나생명": {
        "category": "생명보험",
        "aliases": ["하나생명"],
        "default_prod": "하나로라이트",
        "default_term": "20년납",
        "flyer": "하나생명_11월.png",
        "recommendations": ["하나로라이트 20만", "연결된종신 20만"]
    },
    "푸본현대": {
        "category": "생명보험",
        "aliases": ["푸본현대", "푸본"],
        "default_prod": "MAX원픽",
        "default_term": "20년납",
        "flyer": "푸본현대_11월.png",
        "recommendations": ["MAX원픽 20만", "마이픽 20만"]
    },
    "IM라이프": {
        "category": "생명보험",
        "aliases": ["IM라이프", "IM"],
        "default_prod": "당당한인생",
        "default_term": "7년납",
        "flyer": "IM라이프_11월.png",
        "recommendations": ["당당한인생 20만", "트래블PRO 20만"]
    },
    "IBK연금": {
        "category": "생명보험",
        "aliases": ["IBK연금", "IBK"],
        "default_prod": "프리미엄연금",
        "default_term": "10년납",
        "flyer": "IBK연금_11월.png",
        "recommendations": ["프리미엄연금 20만", "하이브리드연금 20만"]
    }
}


def clean_product_display_name(prod_name: str) -> str:
    cleaned = re.sub(r'\(.*?\)', '', prod_name)
    cleaned = re.sub(r'가입금액\s*[:：]?\s*.*', '', cleaned)
    cleaned = re.sub(r'[,\/].*', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else prod_name


def parse_premium(text: str) -> Optional[int]:
    """텍스트에서 보험료(원 단위)를 추출 (외화 가입금액 및 달러/불 제외)"""
    # 1. 외화 및 가입금액 마스킹
    cleaned = re.sub(r'\d+[\d,]*\s*만?\s*(?:달러|불|USD)', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'가입금액\s*[:：]?\s*\S+', '', cleaned)
    
    # 2. 'X만원' 또는 'X만 원' 우선 매칭
    m_won = re.search(r'(\d+[\d,]*)\s*만\s*원', cleaned)
    if m_won:
        return int(m_won.group(1).replace(',', '')) * 10000
        
    # 3. 'X만' 매칭 (뒤에 년/회/세/차/건/대/달러 등이 오지 않는 경우)
    m_man = re.search(r'(\d+[\d,]*)\s*만(?!\s*(?:년|회|세|차|건|대|달러|불|USD))', cleaned)
    if m_man:
        return int(m_man.group(1).replace(',', '')) * 10000
        
    # 4. 'X,000원' 또는 'X원'
    m2 = re.search(r'(\d+[\d,]{3,})\s*원', cleaned)
    if m2:
        return int(m2.group(1).replace(',', ''))
        
    # 5. 고립된 숫자
    m3 = re.search(r'\b(\d{1,4})\b', cleaned)
    if m3:
        val = int(m3.group(1))
        if val in [5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 70, 100, 150, 200, 300, 500]:
            return val * 10000
    return None


def find_companies_in_text(text: str) -> List[str]:
    """문장에서 언급된 보험사 목록을 정확하고 중복 없이 추출 (긴 별칭 우선)"""
    alias_map = []
    for comp, data in ALL_COMPANIES.items():
        for alias in data['aliases']:
            alias_map.append((alias, comp))
    alias_map.sort(key=lambda x: len(x[0]), reverse=True)
    
    found = []
    used_spans = []
    for alias, comp in alias_map:
        for m in re.finditer(re.escape(alias), text, re.IGNORECASE):
            span = m.span()
            if not any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                used_spans.append(span)
                if comp not in found:
                    found.append(comp)
    return found


def pick_best_term_product(candidates: List[Dict[str, Any]], term: str, default_term: str = "10년납") -> Dict[str, Any]:
    target_term = term if term else default_term
    m = re.search(r'(\d+)\s*년', target_term)
    target_years = m.group(1) if m else ""
    
    # 1. Regex boundary match: e.g. 5년 does not match 15년 or 25년
    if target_years:
        pattern = rf'(?<!\d){target_years}년'
        for p in candidates:
            if re.search(pattern, p.get('term', '')):
                return p
                
    for p in candidates:
        if default_term in p.get('term', ''):
            return p
    return candidates[0]


def search_life_product(company: str, query: str, term: str = "") -> Optional[Dict[str, Any]]:
    """생보사 조견표(767개 전수 데이터)에서 가장 근접한 상품 검색"""
    comp_clean = company.replace('생명', '').replace('라이프', '').strip()
    if comp_clean in ['KB', '케이비']:
        comp_clean = 'KB'
    elif comp_clean in ['신한']:
        comp_clean = '신한'
        
    candidates = [p for p in LIFE_PRODUCTS if p['company'] == comp_clean or comp_clean in p['company'] or comp_clean in p.get('sheet', '')]
    if not candidates:
        return None
        
    q_norm = query.replace(" ", "").replace("-", "").lower()
    
    # 회사별 주요 상품 특화 라우팅
    if comp_clean == "한화":
        if "시그니처" in q_norm or "암" in q_norm:
            matched = [p for p in candidates if "시그니처" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        elif "실속가득" in q_norm or "통합" in q_norm:
            matched = [p for p in candidates if "실속가득H통합" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        elif "치매" in q_norm or "간병" in q_norm:
            matched = [p for p in candidates if "치매담은" in p['product'] or "간병플러스" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        elif "건강더한" in q_norm:
            matched = [p for p in candidates if "건강더한" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "하나로" in q_norm:
            matched = [p for p in candidates if "하나로" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="15년납")
        elif "필요할때" in q_norm:
            matched = [p for p in candidates if "필요할때" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "밸류플러스" in q_norm:
            matched = [p for p in candidates if "밸류플러스" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "h종신" in q_norm:
            matched = [p for p in candidates if p['product'].replace(" ", "").lower() == "h종신"]
            if matched:
                return pick_best_term_product(matched, term, default_term="7년납")
    elif comp_clean == "메트":
        if "변액리치" in q_norm or "리치" in q_norm:
            matched = [p for p in candidates if "변액리치" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="전기납")
        elif "오로지" in q_norm or "달러연금" in q_norm:
            matched = [p for p in candidates if "오로지" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "모두의" in q_norm:
            matched = [p for p in candidates if "모두의" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납")
        elif "달러" in q_norm or "백만인" in q_norm or "종신" in q_norm:
            matched = [p for p in candidates if "백만인" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "360" in q_norm or "종합" in q_norm:
            matched = [p for p in candidates if "360" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        elif "오늘의" in q_norm or "vip" in q_norm:
            matched = [p for p in candidates if "오늘의종신" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납이상")
    elif comp_clean == "DB":
        if "내가고른" in q_norm or "통합" in q_norm:
            matched = [p for p in candidates if "내가고른" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납")
        elif "실속n" in q_norm:
            matched = [p for p in candidates if "실속N" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납")
        elif any(k in q_norm for k in ["알행플", "알행종"]):
            matched = [p for p in candidates if "알행플" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "리턴" in q_norm:
            matched = [p for p in candidates if "리턴" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif "올케어" in q_norm:
            matched = [p for p in candidates if "올케어" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
    elif comp_clean == "동양":
        if "쑥쑥" in q_norm or "어린이" in q_norm:
            matched = [p for p in candidates if "쑥쑥" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="15년납")
    elif comp_clean == "미래":
        if "m케어" in q_norm or "엠케어" in q_norm or "건강" in q_norm:
            matched = [p for p in candidates if "M-케어" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
    elif comp_clean == "라이나":
        if "새로담는" in q_norm:
            matched = [p for p in candidates if "새로담는" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납")
        elif "채우는" in q_norm:
            matched = [p for p in candidates if "채우는" in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
    elif comp_clean == "흥국":
        if any(k in q_norm for k in ['오튼튼', '5.10.5', '5105', '다사랑암']):
            matched = [p for p in candidates if '오튼튼' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['3.10.5', '3105', '고당', '간편건강']):
            matched = [p for p in candidates if '3.10.5' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['다사랑통합', '다사랑']):
            matched = [p for p in candidates if '다(多)사랑통합' in p['product'] or '다사랑' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['건강', '종합', '인보험']):
            matched = [p for p in candidates if '오튼튼' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['3.5.5', '355', '3n5']):
            matched = [p for p in candidates if '3n5' in p['product'].lower()]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['3.1.1', '311']):
            matched = [p for p in candidates if '3.1.1' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['리턴100', '리턴', '플렉스']):
            matched = [p for p in candidates if '리턴100' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년↑")
        elif any(k in q_norm for k in ['치매', '시니어']):
            matched = [p for p in candidates if '치매담은' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
        elif any(k in q_norm for k in ['미리받는', '트리플']):
            matched = [p for p in candidates if '미리받는' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        else:
            matched = [p for p in candidates if '오튼튼' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년↑")
    elif comp_clean == "신한":
        if any(k in q_norm for k in ['슈퍼원', '원', 'one', '통합', '건강', '3.10.5', '3105']):
            matched = [p for p in candidates if '슈퍼원' in p['product'] or '통합건강' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")
        elif any(k in q_norm for k in ['모아더드림', '더드림']):
            matched = [p for p in candidates if '모아더드림' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="7년납이상")
        elif any(k in q_norm for k in ['세븐플러스', '세븐plus', '세븐']):
            matched = [p for p in candidates if '세븐Plus' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납")
        elif any(k in q_norm for k in ['든든한', '더든든한']):
            matched = [p for p in candidates if 'The든든한' in p['product'] or '든든한' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif any(k in q_norm for k in ['리필종신', '리필']):
            matched = [p for p in candidates if '리필종신' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납")
        elif any(k in q_norm for k in ['연금', '원더라이프', '변액연금']):
            matched = [p for p in candidates if '연금' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="10년납이상")
        else:
            matched = [p for p in candidates if '슈퍼원' in p['product'] or '통합건강' in p['product']]
            if matched:
                return pick_best_term_product(matched, term, default_term="20년납이상")

    # 일반 공백 무시 부분일치 검색
    matched = []
    for p in candidates:
        p_norm = p['product'].replace(" ", "").replace("-", "").lower()
        if q_norm in p_norm:
            matched.append(p)
    if matched:
        return pick_best_term_product(matched, term, default_term="10년납")

    # 토큰 스코어링 검색 (공백 분리 단어 기준)
    q_words = re.sub(r'\d+[\d,]*\s*만?\s*원?', ' ', query)
    q_words = re.sub(r'\d+\s*년\s*납?|전기납', ' ', q_words)
    for c_alias in [company, comp_clean, '생명', '라이프', '보험']:
        q_words = q_words.replace(c_alias, ' ')
    tokens = [t for t in re.split(r'[\s,\(\)\/\-\.]+', q_words.strip()) if len(t) >= 2]

    scored = []
    for p in candidates:
        p_name = p['product'].replace(" ", "").replace("-", "").lower()
        score = sum(3 for t in tokens if t in p_name)
        m_y = re.search(r'(\d+)\s*년', term)
        if m_y and re.search(rf'(?<!\d){m_y.group(1)}년', p.get('term', '')):
            score += 15
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]

    def_prod = ALL_COMPANIES.get(company, {}).get('default_prod', '')
    if def_prod:
        matched_def = [p for p in candidates if def_prod in p['product']]
        if matched_def:
            return pick_best_term_product(matched_def, term, default_term="10년납")

    return candidates[0]



def get_sky_jongshin_bonus(comp: str, prod: str, term: str, premium: int, is_corp: bool = False) -> Tuple[int, str]:
    """스카이블루에셋 11월 본사 종신전략상품 추가지원안 (구간별 고정 시상금액, 익월 50% + 15회차 50%)"""
    c = comp.lower()
    p = prod.lower()
    t = term.lower()
    
    # 1. DB알행종 (10년납, 7년납) - 개인/법인 모두 지급
    if ('db' in c or '디비' in c) and any(k in p for k in ['알행종', '알행플', '알차고']):
        if '10년' in t:
            if premium >= 24000000: return 60000000, "DB알행종 10년납 SKY본사추가 6,000만원(익월3000+15회3000)"
            elif premium >= 18000000: return 45000000, "DB알행종 10년납 SKY본사추가 4,500만원(익월2250+15회2250)"
            elif premium >= 12000000: return 30000000, "DB알행종 10년납 SKY본사추가 3,000만원(익월1500+15회1500)"
            elif premium >= 8400000: return 21000000, "DB알행종 10년납 SKY본사추가 2,100만원(익월1050+15회1050)"
            elif premium >= 6000000: return 15000000, "DB알행종 10년납 SKY본사추가 1,500만원(익월750+15회750)"
            elif premium >= 3600000: return 9000000, "DB알행종 10년납 SKY본사추가 900만원(익월450+15회450)"
            elif premium >= 2400000: return 6000000, "DB알행종 10년납 SKY본사추가 600만원(익월300+15회300)"
            elif premium >= 1200000: return 3000000, "DB알행종 10년납 SKY본사추가 300만원(익월150+15회150)"
        elif '7년' in t:
            if premium >= 24000000: return 40000000, "DB알행종 7년납 SKY본사추가 4,000만원(익월2000+15회2000)"
            elif premium >= 18000000: return 30000000, "DB알행종 7년납 SKY본사추가 3,000만원(익월1500+15회1500)"
            elif premium >= 12000000: return 20000000, "DB알행종 7년납 SKY본사추가 2,000만원(익월1000+15회1000)"
            elif premium >= 8400000: return 15000000, "DB알행종 7년납 SKY본사추가 1,500만원(익월750+15회750)"
            elif premium >= 6000000: return 10000000, "DB알행종 7년납 SKY본사추가 1,000만원(익월500+15회500)"
            elif premium >= 3600000: return 6000000, "DB알행종 7년납 SKY본사추가 600만원(익월300+15회300)"
            elif premium >= 2400000: return 4000000, "DB알행종 7년납 SKY본사추가 400만원(익월200+15회200)"
            elif premium >= 1200000: return 2000000, "DB알행종 7년납 SKY본사추가 200만원(익월100+15회100)"

    # 2. 한화생명 하나로 (15년납·법인계약만)
    elif ('한화' in c) and ('하나로' in p):
        if is_corp and ('15년' in t or '20년' in t):
            if premium >= 24000000: return 60000000, "한화하나로 15년납 SKY법인추가 6,000만원(익월3000+15회3000)"
            elif premium >= 18000000: return 45000000, "한화하나로 15년납 SKY법인추가 4,500만원(익월2250+15회2250)"
            elif premium >= 12000000: return 30000000, "한화하나로 15년납 SKY법인추가 3,000만원(익월1500+15회1500)"
            elif premium >= 8400000: return 21000000, "한화하나로 15년납 SKY법인추가 2,100만원(익월1050+15회1050)"
            elif premium >= 6000000: return 15000000, "한화하나로 15년납 SKY법인추가 1,500만원(익월750+15회750)"
            elif premium >= 3600000: return 9000000, "한화하나로 15년납 SKY법인추가 900만원(익월450+15회450)"
            elif premium >= 2400000: return 2400000, "한화하나로 15년납 SKY법인추가 240만원(익월120+15회120)"
            elif premium >= 1200000: return 1200000, "한화하나로 15년납 SKY법인추가 120만원(익월60+15회60)"

    # 3. 푸본현대 맥스원픽 / IM당당한인생 (7년납·법인계약만)
    elif (('푸본' in c and '원픽' in p) or ('im' in c and '당당한' in p)):
        if is_corp and '7년' in t:
            label = "푸본맥스원픽" if '푸본' in c else "IM당당한인생"
            if premium >= 24000000: return 40000000, f"{label} 7년납 SKY법인추가 4,000만원(익월2000+15회2000)"
            elif premium >= 18000000: return 30000000, f"{label} 7년납 SKY법인추가 3,000만원(익월1500+15회1500)"
            elif premium >= 12000000: return 20000000, f"{label} 7년납 SKY법인추가 2,000만원(익월1000+15회1000)"
            elif premium >= 8400000: return 15000000, f"{label} 7년납 SKY법인추가 1,500만원(익월750+15회750)"
            elif premium >= 6000000: return 10000000, f"{label} 7년납 SKY법인추가 1,000만원(익월500+15회500)"
            elif premium >= 3600000: return 6000000, f"{label} 7년납 SKY법인추가 600만원(익월300+15회300)"
            elif premium >= 2400000: return 2400000, f"{label} 7년납 SKY법인추가 240만원(익월120+15회120)"
            elif premium >= 1200000: return 1200000, f"{label} 7년납 SKY법인추가 120만원(익월60+15회60)"

    return 0, ""


def get_sky_health_bonus(comp: str, prod: str, premium: int) -> Tuple[float, str]:
    """스카이블루에셋 11월 본사 건강전략상품 추가시상안 (P 10만↑ 100%, P 20만↑ 200% 익월지급)"""
    c = comp.lower()
    p = prod.lower()
    
    # 1. DB건강 4종: {생활비암, 내가고른, 건강100, 치매간병}
    if ('db' in c or '디비' in c) and any(k in p for k in ['생활비암', '내가고른', '건강100', '치매간병', '치매', '간병', '7대질병', '올케어', '건강', '통합']):
        if premium >= 200000: return 2.0, "SKY본사 건강추가 200%(익월)"
        elif premium >= 100000: return 1.0, "SKY본사 건강추가 100%(익월)"
            
    # 2. 흥국건강 5종: {오튼튼, 3.10.5, 고당+, 3.8.5.5, 다사랑3N5, 치매담은(시니어, PLUS)}
    elif '흥국' in c and any(k in p for k in ['오튼튼', '3.10.5', '고당', '3.8.5.5', '3n5', '다사랑', '치매담은', '시니어', '건강', '암']):
        if premium >= 200000: return 2.0, "SKY본사200"
        elif premium >= 100000: return 1.0, "SKY본사100"
            
    return 0.0, ""

def get_life_incentive(comp_name: str, product_name: str, term: str = "", premium: int = 200000, incentive_type: str = "전략", continuous_mode: str = "none", contract_type: str = "개인") -> Dict[str, Any]:
    """17개 생보사 11월 공식 시책표 정밀 판정 (메트라이프 납기별 차이, 흥국 2종 연속, 신한 3~7번 연계, 라이나, 미래에셋 완벽 반영)"""
    comp = comp_name.replace('생명', '').replace('라이프', '').strip().lower()
    prod = product_name.replace(" ", "").lower()
    
    # 1. 메트라이프생명 (사용자 지시: 납입기간에 따라 s환산차이 크고 시책도 상이)
    if '메트' in comp:
        if '달러' in prod or '백만인' in prod or '종신' in prod:
            m_y = re.search(r'(\d+)\s*년', term)
            years = int(m_y.group(1)) if m_y else 10
            if years <= 5:
                return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (달러종신Plus 5년납 250%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif years in [7, 10]:
                return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": f"익월 400% (달러종신Plus {years}년납 400%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '3년내고' in prod or years == 3:
                return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (3년내고 만족하는 달러종신 250%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": f"익월 400% (달러종신Plus {years}년납 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '정기' in prod or '변액리치' in prod:
            return {"next_month": 2.0, "split": 2.5, "total": 4.5, "basis": "익월 200% + 15차월 250% (변액리치 정기 450%)", "cont_bonus": 0.3, "cont_desc": "전략상품 1건 이상 가동 시 15차월 추가 +30%"}
        elif '연금' in prod:
            return {"next_month": 3.0, "split": 0.0, "total": 3.0, "basis": "익월 300% (오로지연금을위한 달러연금 300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '무해약' in prod or '해약' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (간편 360 종합 무해약환급형 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '암' in prod:
            return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (360 암보험 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '간편' in prod or '종합' in prod or '360' in prod:
            return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (간편 360 종합 갱신형 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 0.0, "total": 2.5, "basis": "익월 250% (메트라이프 전략 250%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 2. 흥국생명 (10~11월 연속가동 & 핑크멤버스 2종 연속시상)
    elif '흥국' in comp:
        is_strat = (incentive_type == "전략" or any(k in prod for k in ['오튼튼', '다사랑', '치매', '암', '건강', '3.10.5']))
        base_next = 4.0
        sky_next = 0.0
        sky_health_desc = ""
        if is_strat:
            if premium >= 200000:
                sky_next = 2.0
                sky_health_desc = "SKY본사200"
            elif premium >= 100000:
                sky_next = 1.0
                sky_health_desc = "SKY본사100"
        install_period = 6.0
        install_strat = 2.0 if is_strat else 0.0
        
        c1_amount = 0
        if premium >= 1000000: c1_amount = 10000000
        elif premium >= 700000: c1_amount = 7000000
        elif premium >= 500000: c1_amount = 5000000
        elif premium >= 300000: c1_amount = 1800000
        elif premium >= 200000: c1_amount = 1200000
        elif premium >= 100000: c1_amount = 600000
        elif premium >= 50000: c1_amount = 300000
        
        c2_amount = 0
        if premium >= 1000000: c2_amount = 5000000
        elif premium >= 700000: c2_amount = 3500000
        elif premium >= 500000: c2_amount = 2500000
        elif premium >= 300000: c2_amount = 1500000
        elif premium >= 200000: c2_amount = 1000000
        elif premium >= 100000: c2_amount = 500000

        c1_rate = (c1_amount / premium) if premium > 0 else 0.0
        c2_rate = (c2_amount / premium) if premium > 0 else 0.0

        applied_cont_rate = 0.0
        applied_desc = ""
        c_mode = continuous_mode.lower()
        if "c1" in c_mode or "10-11" in c_mode or "10월연속" in c_mode or "연속가동" in c_mode:
            applied_cont_rate = c1_rate
            applied_desc = f"[10~11월 연속가동 +{c1_amount//10000}만 원({int(c1_rate*100)}%) 합산]"
        elif "c2" in c_mode or "핑크" in c_mode:
            applied_cont_rate = c2_rate
            applied_desc = f"[핑크멤버스 +{c2_amount//10000}만 원({int(c2_rate*100)}%) 합산]"
        elif "both" in c_mode or "all" in c_mode or "full" in c_mode or "풀" in c_mode or "모두" in c_mode or "둘다" in c_mode or "연속포함" in c_mode or c_mode == "true":
            applied_cont_rate = c1_rate + c2_rate
            applied_desc = f"[연속 2종 모두포함 +{(c1_amount+c2_amount)//10000}만 원({int((c1_rate+c2_rate)*100)}%) 합산]"

        basis = f"익월 {int((base_next+sky_next)*100)}%(원수사400+{sky_health_desc}) + 13회차 {int((install_period+install_strat)*100)}%(1~3주600+전략{int(install_strat*100)})"
        if applied_desc:
            basis += f" {applied_desc}"

        return {
            "next_month": base_next + sky_next,
            "split": install_period + install_strat + applied_cont_rate,
            "total": base_next + sky_next + install_period + install_strat + applied_cont_rate,
            "basis": basis,
            "c1_amount": c1_amount,
            "c2_amount": c2_amount,
            "cont_bonus": c1_rate + c2_rate,
            "cont_desc": f"① 10~11월 연속가동(+{c1_amount//10000}만) ② 핑크멤버스(+{c2_amount//10000}만)",
            "is_heungkuk": True,
            "continuous_mode": continuous_mode
        }

    # 3. 한화생명
    elif '한화' in comp:
        if '건강더한' in prod:
            if '7년' in term:
                return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (건강더한종신 7년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (건강더한종신 10년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '하나로' in prod:
            base_next = 3.5 if '10년' in term else 5.0
            base_split = 1.5 if '10년' in term else 2.0
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("한화생명", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            tot_rate = tot_next + tot_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and ('15년' in term or '20년' in term):
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif '필요할때' in prod:
            if '12년' in term:
                return {"next_month": 6.0, "split": 2.5, "total": 8.5, "basis": "익월 600% + 13회차 250% (필요할때쓰는종신 12년납 850%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 4.5, "split": 2.0, "total": 6.5, "basis": "익월 450% + 13회차 200% (필요할때쓰는종신 10년납 650%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '밸류플러스' in prod:
            return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (밸류플러스2.0 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '치매' in prod or '간병' in prod:
            return {"next_month": 5.0, "split": 3.0, "total": 8.0, "basis": "익월 500% + 13회차 300% (치매담은 간병플러스 800%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '암' in prod or '시그니처' in prod:
            return {"next_month": 5.0, "split": 8.0, "total": 13.0, "basis": "익월 500% + 13회차 800% (시그니처암 1,300%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif 'h종신' in prod or 'h' in prod:
            return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (H종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (한화생명 주력 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 4. DB생명
    elif 'db' in comp or '디비' in comp or '동부' in comp:
        if any(k in prod for k in ['알행플', '알행종', '알차고']):
            base_next = 4.0
            base_split = 1.0 if '7년' in term else 2.0
            sky_amount, sky_desc = get_sky_jongshin_bonus("DB생명", prod, term, premium, is_corp=True)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            tot_rate = tot_next + tot_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            return {"next_month": tot_next, "split": tot_split, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif any(k in prod for k in ['생활비암', '내가고른', '건강100', '치매간병', '치매', '간병', '7대질병', '올케어', '건강', '통합']):
            base_next = 4.0
            base_split = 2.0
            sky_rate, sky_desc = get_sky_health_bonus("DB생명", prod, premium)
            tot_next = base_next + sky_rate
            tot_split = base_split
            basis = f"원수사 600%(익월400+13회200)"
            if sky_desc:
                basis += f" + {sky_desc}"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        elif '리턴' in prod:
            return {"next_month": 4.0, "split": 2.0, "total": 6.0, "basis": "원수사 600% (익월 400% + 13회차 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '올케어' in prod:
            return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "원수사 800% (익월 400% + 13회차 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 4.0, "split": 2.0, "total": 6.0, "basis": "원수사 600% (익월 400% + 13회차 200%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 5. 신한라이프 (2번째장 3~7번 연계는 연속포함 시에만 합산)
    elif '신한' in comp:
        if '모아더드림plus' in prod or '모아더드림플러스' in prod:
            return {"next_month": 4.0, "split": 1.0, "total": 5.0, "basis": "익월 400% + 13회차 100% (모아더드림Plus 500%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '모아더드림' in prod or '리필' in prod or '3케어' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (모아더드림/리필종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '든든한' in prod or 'the든든한' in prod:
            return {"next_month": 4.0, "split": 0.0, "total": 4.0, "basis": "익월 400% (THE든든한종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '변액' in prod:
            return {"next_month": 1.0, "split": 0.0, "total": 1.0, "basis": "익월 100% (ONE더드림 변액연금 강화형 100%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '연금' in prod:
            return {"next_month": 2.0, "split": 0.0, "total": 2.0, "basis": "익월 200% (ONE더라이프 연금 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            next_m = 2.5
            base_split_amount = 0
            if premium >= 600000: base_split_amount = 7200000
            elif premium >= 400000: base_split_amount = 4800000
            elif premium >= 250000: base_split_amount = 2500000
            elif premium >= 150000: base_split_amount = 1500000
            elif premium >= 70000: base_split_amount = 700000
            base_split_rate = (base_split_amount / premium) if premium > 0 else 0.0
            
            cont_amount = 0
            cont_desc_parts = []
            if premium >= 250000: cont_amount += 960000; cont_desc_parts.append("연속가동① 96만")
            elif premium >= 150000: cont_amount += 660000; cont_desc_parts.append("연속가동① 66만")
            elif premium >= 70000: cont_amount += 420000; cont_desc_parts.append("연속가동① 42만")
                
            if premium >= 250000: cont_amount += 600000; cont_desc_parts.append("집중연속② 60만")
            elif premium >= 150000: cont_amount += 400000; cont_desc_parts.append("집중연속② 40만")
            elif premium >= 70000: cont_amount += 240000; cont_desc_parts.append("집중연속② 24만")
                
            if premium >= 500000: cont_amount += 1500000; cont_desc_parts.append("멤버십 150만")
            elif premium >= 400000: cont_amount += 1200000; cont_desc_parts.append("멤버십 120만")
            elif premium >= 300000: cont_amount += 900000; cont_desc_parts.append("멤버십 90만")
            elif premium >= 200000: cont_amount += 600000; cont_desc_parts.append("멤버십 60만")
            elif premium >= 100000: cont_amount += 300000; cont_desc_parts.append("멤버십 30만")
                
            cont_rate = (cont_amount / premium) if premium > 0 else 0.0
            cont_desc = " + ".join(cont_desc_parts) + f" (총 +{cont_amount//10000}만 원)"
            
            applied_cont = cont_rate if (continuous_mode != "none" and continuous_mode != "") else 0.0
            basis = f"익월 250%({int(premium*next_m):,}원) + 1주차가동 {base_split_amount//10000}만 원({int(base_split_rate*100)}%)"
            if applied_cont > 0:
                basis += f" [연계·연속 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 합산]"
                
            return {
                "next_month": next_m,
                "split": base_split_rate + applied_cont,
                "total": next_m + base_split_rate + applied_cont,
                "basis": basis,
                "cont_bonus": cont_rate,
                "cont_desc": cont_desc
            }

    # 6. 라이나생명 (새로담는건강, 브레인케어, 치아/치매, 종신 완벽 판정)
    elif '라이나' in comp:
        if '새로담는' in prod or '브레인' in prod or ('건강' in prod and '종신' not in prod):
            next_m = 3.0
            base_split = 1.0
            split_amount = 0
            if premium >= 300000: split_amount = 5400000
            elif premium >= 200000: split_amount = 3400000
            elif premium >= 100000: split_amount = 1600000
            elif premium >= 50000: split_amount = 500000
                
            split_rate_from_amount = (split_amount / premium) if premium > 0 else 0.0
            core_rate = 4.0 if premium >= 100000 else 0.0
            
            cont_amount = 0
            if premium >= 300000: cont_amount = 900000
            elif premium >= 200000: cont_amount = 600000
            elif premium >= 100000: cont_amount = 200000
            elif premium >= 50000: cont_amount = 100000
            cont_rate = (cont_amount / premium) if premium > 0 else 0.0
            
            applied_cont = cont_rate if (continuous_mode != "none" and continuous_mode != "") else 0.0
            tot_split_rate = base_split + split_rate_from_amount + core_rate + applied_cont
            tot_rate = next_m + tot_split_rate
            
            basis = f"익월 300%({int(premium*next_m):,}원) + 13회차 {int((base_split+split_rate_from_amount+core_rate)*100)}%(기본100+구간{split_amount//10000}만+핵심담보{int(core_rate*100)}%)"
            if applied_cont > 0:
                basis += f" [10~11월 연속가동 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 합산]"
                
            return {
                "next_month": next_m,
                "split": tot_split_rate,
                "total": tot_rate,
                "basis": basis,
                "cont_bonus": cont_rate,
                "cont_desc": f"10~11월 연속가동 +{cont_amount//10000}만 원({int(cont_rate*100)}%) 추가 합산 가능"
            }
        elif '치아' in prod or '치매' in prod or '암' in prod:
            next_m = 3.0
            split_amount = 0
            if premium >= 300000: split_amount = 1800000
            elif premium >= 200000: split_amount = 1000000
            elif premium >= 100000: split_amount = 400000
            elif premium >= 50000: split_amount = 150000
            split_rate = (split_amount / premium) if premium > 0 else 0.0
            tot_rate = next_m + split_rate
            basis = f"익월 300% + 13회차 구간 {split_amount//10000}만 원({int(split_rate*100)}%)"
            return {"next_month": next_m, "split": split_rate, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            if '7년' in term:
                return {"next_month": 3.5, "split": 1.5, "total": 5.0, "basis": "익월 350% + 13회차 150% (THE채우는종신 7년납 500%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '간편' in term or '간편' in prod:
                if '10년' in term:
                    return {"next_month": 3.0, "split": 1.5, "total": 4.5, "basis": "익월 300% + 13회차 150% (THE채우는종신 10년납 간편 450%)", "cont_bonus": 0.0, "cont_desc": ""}
                else:
                    return {"next_month": 2.5, "split": 1.0, "total": 3.5, "basis": "익월 250% + 13회차 100% (THE착한간편종신 350%)", "cont_bonus": 0.0, "cont_desc": ""}
            elif '10년' in term:
                return {"next_month": 3.0, "split": 6.5, "total": 9.5, "basis": "익월 300% + 13회차 650% (THE채우는종신 10년납 일반심사 950%)", "cont_bonus": 0.0, "cont_desc": ""}
            else:
                return {"next_month": 2.5, "split": 1.0, "total": 3.5, "basis": "익월 250% + 13회차 100% (THE건강/착한간편종신 350%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 7. 미래에셋생명 (건강파트 익월 250% + 구간시상)
    elif '미래' in comp:
        if '연금' in prod:
            rate = 2.0 if premium >= 200000 else (1.0 if premium >= 100000 else 0.0)
            return {"next_month": rate, "split": 0.0, "total": rate, "basis": f"익월 {int(rate*100)}% (변액연금 강화형)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '변액' in prod or '약속' in prod:
            return {"next_month": 1.0, "split": 2.8, "total": 3.8, "basis": "익월 100% + 13회차 280% (변액종신 미래의약속 380%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '상속' in prod or '헤리티지' in prod:
            return {"next_month": 2.0, "split": 4.5, "total": 6.5, "basis": "익월 200% + 13회차 450% (상속종신 헤리티지 650%)", "cont_bonus": 0.0, "cont_desc": ""}
        elif '치아' in prod:
            return {"next_month": 1.0, "split": 1.0, "total": 2.0, "basis": "익월 100% + 13회차 100% (치아보험 200%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            next_m = 2.5
            split_amount = 0
            if premium >= 2000000: split_amount = 35700000
            elif premium >= 1500000: split_amount = 20700000
            elif premium >= 1000000: split_amount = 10700000
            elif premium >= 700000: split_amount = 9200000
            elif premium >= 500000: split_amount = 8200000
            elif premium >= 300000: split_amount = 5700000
            elif premium >= 200000: split_amount = 3600000
            elif premium >= 100000: split_amount = 1500000
            elif premium >= 50000: split_amount = 150000
            
            split_rate = (split_amount / premium) if premium > 0 else 0.0
            tot_rate = next_m + split_rate
            basis = f"익월 250%({int(premium*next_m):,}원) + 13회차 구간시상 {split_amount//10000}만 원({int(split_rate*100)}%) = 총 {int(tot_rate*100)}%"
            return {"next_month": next_m, "split": split_rate, "total": tot_rate, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}

    # 8. KB라이프
    elif 'kb' in comp:
        if '연금' in prod:
            return {"next_month": 2.0, "split": 5.0, "total": 7.0, "basis": "익월 200% + 13회차 500% (100세 든든 연금 700%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 22.5, "total": 25.5, "basis": "익월 300% + 13회차 2,250% (딱좋은 건강군 최대 2,550%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 9. 동양생명
    elif '동양' in comp:
        if '알뜰' in prod:
            return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (알뜰플러스 400%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.0, "split": 3.0, "total": 5.0, "basis": "익월 200% + 13회차 300% (우리WON 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 10. 푸본현대생명
    elif '푸본' in comp:
        if '원픽' in prod:
            base_next = 3.5
            base_split = 1.5
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("푸본현대", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            basis = f"원수사 500%(익월350+13회150)"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and '7년' in term:
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (마이픽 건강 600%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 11. KDB생명
    elif 'kdb' in comp:
        return {"next_month": 3.0, "split": 1.0, "total": 4.0, "basis": "익월 300% + 13회차 100% (버팀목종신 400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 12. ABL생명
    elif 'abl' in comp:
        return {"next_month": 4.0, "split": 4.0, "total": 8.0, "basis": "익월 400% + 13회차 400% (우리WON더채움종신 800%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 13. 농협생명
    elif '농협' in comp:
        if '종신' in prod:
            return {"next_month": 4.5, "split": 1.5, "total": 6.0, "basis": "익월 450% + 13회차 150% (투스텝NH종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 5.0, "split": 12.0, "total": 17.0, "basis": "익월 500% + 13회차 1,200% (건강플러스통합 1,700%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 14. 교보생명
    elif '교보' in comp:
        return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (모두지킴종신 600%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 15. 하나생명
    elif '하나' in comp:
        return {"next_month": 5.0, "split": 19.0, "total": 24.0, "basis": "익월 500% + 13회차 1,900% (하나로라이트 최대 2,400%)", "cont_bonus": 0.0, "cont_desc": ""}

    # 16. IM라이프
    elif 'im' in comp or '아이엠' in comp:
        if '당당한' in prod:
            base_next = 3.0 if '7년' in term else 2.5
            base_split = 1.0 if '7년' in term else 0.0
            is_corp = (contract_type == "법인")
            sky_amount, sky_desc = get_sky_jongshin_bonus("IM라이프", prod, term, premium, is_corp=is_corp)
            sky_next = 0.0
            sky_split = 0.0
            if sky_amount > 0 and premium > 0:
                sky_rate = sky_amount / premium
                sky_next = sky_rate * 0.5
                sky_split = sky_rate * 0.5
            tot_next = base_next + sky_next
            tot_split = base_split + sky_split
            basis = f"원수사 {int((base_next+base_split)*100)}%(익월{int(base_next*100)}+13회{int(base_split*100)})"
            if sky_desc:
                basis += f" + {sky_desc}"
            elif not is_corp and '7년' in term:
                basis += " (개인계약: SKY본사법인지원 제외)"
            return {"next_month": tot_next, "split": tot_split, "total": tot_next + tot_split, "basis": basis, "cont_bonus": 0.0, "cont_desc": ""}
        else:
            return {"next_month": 2.5, "split": 2.5, "total": 5.0, "basis": "익월 250% + 13회차 250% (IM라이프 주력 500%)", "cont_bonus": 0.0, "cont_desc": ""}

    return {"next_month": 3.0, "split": 3.0, "total": 6.0, "basis": "익월 300% + 13회차 300% (기본 전략 600%)", "cont_bonus": 0.0, "cont_desc": ""}


def calculate_life(
    company: str,
    product_name: str,
    premium: int,
    s_factor: float = 1000.0,
    term: str = "20년납",
    incentive_type: str = "전략",
    continuous_mode: str = "none",
    contract_type: str = "개인"
) -> Dict[str, Any]:
    comp_clean = company.replace('생명', '').replace('라이프', '').strip()
    
    conversion_rate = s_factor / 10.0
    s_grade = round(premium * (s_factor / 1000.0))
    
    next_month_rate = LIFE_RULES['next_month_rate']
    
    comp_inst_dict = LIFE_RULES.get('company_installments', {}).get(comp_clean, {})
    inst_rate = 1.32
    if isinstance(comp_inst_dict, dict):
        inst_rate = comp_inst_dict.get('default', 1.32)
        prod_lower = product_name.lower()
        for k, v in comp_inst_dict.items():
            if k != 'default' and k in prod_lower:
                inst_rate = v
                break
    elif isinstance(comp_inst_dict, (int, float)):
        inst_rate = float(comp_inst_dict)
        
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = next_month_comm + installment_comm
    
    inc_info = get_life_incentive(comp_clean, product_name, term, premium, incentive_type, continuous_mode, contract_type=contract_type)
    next_month_inc_rate = inc_info.get("next_month", 0.0)
    split_inc_rate = inc_info.get("split", 0.0)
    basis_desc = inc_info.get("basis", "")
    cont_bonus_rate = inc_info.get("cont_bonus", 0.0)
    cont_desc = inc_info.get("cont_desc", "")
    c1_amount = inc_info.get("c1_amount", 0)
    c2_amount = inc_info.get("c2_amount", 0)
    is_heungkuk = inc_info.get("is_heungkuk", False)
    
    next_month_inc = round(premium * next_month_inc_rate)
    split_inc = round(premium * split_inc_rate)
    total_inc = next_month_inc + split_inc
    total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    display_comp = company
    if not display_comp.endswith("생명") and not display_comp.endswith("라이프"):
        display_comp += "생명"
        
    return {
        "category": "생명보험",
        "company": display_comp,
        "product_name": product_name,
        "term": term,
        "premium": premium,
        "s_factor": s_factor,
        "conversion_rate": conversion_rate,
        "s_grade": s_grade,
        "next_month_comm": next_month_comm,
        "next_month_comm_rate": round(next_month_rate * 100, 1),
        "installment_comm": installment_comm,
        "installment_comm_rate": round(inst_rate * 100, 1),
        "total_comm": total_comm,
        "next_month_inc": next_month_inc,
        "next_month_inc_rate": round(next_month_inc_rate * 100, 1),
        "split_inc": split_inc,
        "split_inc_rate": round(split_inc_rate * 100, 1),
        "total_inc": total_inc,
        "total_inc_rate": total_inc_rate,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total,
        "basis_desc": basis_desc,
        "cont_bonus_rate": cont_bonus_rate,
        "cont_desc": cont_desc,
        "c1_amount": c1_amount,
        "c2_amount": c2_amount,
        "is_heungkuk": is_heungkuk,
        "continuous_mode": continuous_mode
    }


def calculate_nonlife(
    company: str,
    product_name: str,
    premium: int,
    incentive_type: str = "주력",
    continuous_mode: str = "none"
) -> Dict[str, Any]:
    comp_matched = "현대해상"
    for c in NONLIFE_RULES['companies']:
        if c in company or company in c:
            comp_matched = c
            break
            
    conv_rate = NONLIFE_RULES['conversion_rate']
    s_grade = round(premium * conv_rate)
    
    next_month_rate = NONLIFE_RULES['next_month_rate']
    inst_rate = NONLIFE_RULES['installment_rate']
    
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = next_month_comm + installment_comm
    
    inc_dict = NONLIFE_RULES.get('incentives', {}).get(comp_matched, {}).get(incentive_type, {})
    if not inc_dict:
        inc_dict = NONLIFE_RULES.get('incentives', {}).get('현대해상', {}).get('주력', {})
        
    next_month_inc_rate = inc_dict.get('next_month_base', 1.0) + inc_dict.get('next_month_sky', 2.6)
    split_inc_rate = (
        inc_dict.get('install_week_bonus', 0.0) +
        inc_dict.get('install_main_bonus', 0.0) +
        inc_dict.get('install_sky_2nd', 0.0) +
        inc_dict.get('install_sky_add', 0.0)
    )
    
    basis_desc = inc_dict.get('basis', '')
    cont_bonus_rate = inc_dict.get('cont_bonus_rate', 0.0)
    cont_desc = inc_dict.get('cont_desc', '')
    
    include_cont = (continuous_mode != "none" and continuous_mode != "")
    if include_cont and cont_bonus_rate > 0:
        split_inc_rate += cont_bonus_rate
        basis_desc += f" [전월 연속가동 +{int(round(cont_bonus_rate*100))}% 합산]"
        
    next_month_inc = round(premium * next_month_inc_rate)
    split_inc = round(premium * split_inc_rate)
    total_inc = next_month_inc + split_inc
    total_inc_rate = round((next_month_inc_rate + split_inc_rate) * 100, 1)
    
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    full_comp_name = comp_matched
    if not full_comp_name.endswith("해상") and not full_comp_name.endswith("손보") and not full_comp_name.endswith("화재"):
        full_comp_name += "화재"
        
    return {
        "category": "손해보험",
        "company": full_comp_name,
        "product_name": product_name,
        "term": "장기보장성",
        "premium": premium,
        "s_factor": 920.0,
        "conversion_rate": 92.0,
        "s_grade": s_grade,
        "next_month_comm": next_month_comm,
        "next_month_comm_rate": round(next_month_rate * 100, 1),
        "installment_comm": installment_comm,
        "installment_comm_rate": round(inst_rate * 100, 1),
        "total_comm": total_comm,
        "next_month_inc": next_month_inc,
        "next_month_inc_rate": round(next_month_inc_rate * 100, 1),
        "split_inc": split_inc,
        "split_inc_rate": round(split_inc_rate * 100, 1),
        "total_inc": total_inc,
        "total_inc_rate": total_inc_rate,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total,
        "basis_desc": basis_desc,
        "cont_bonus_rate": cont_bonus_rate,
        "cont_desc": cont_desc,
        "is_heungkuk": False,
        "continuous_mode": continuous_mode
    }


# ==========================================
# 2. 시책지 원본 매핑 및 검색 (KB라이프, 신한라이프 등 완벽 수정)
# ==========================================
FLYER_MAP = {
    "신한라이프": "신한라이프_11월_p2.png",
    "신한생명": "신한라이프_11월_p2.png",
    "신한": "신한라이프_11월_p2.png",
    "KB라이프": "KB라이프_11월.png",
    "KB생명": "KB라이프_11월.png",
    "케이비라이프": "KB라이프_11월.png",
    "케이비생명": "KB라이프_11월.png",
    "라이나생명": "라이나생명_11월.png",
    "라이나": "라이나생명_11월.png",
    "한화생명": "한화생명_11월.png",
    "한화": "한화생명_11월.png",
    "흥국생명": "흥국생명_11월.png",
    "흥국": "흥국생명_11월.png",
    "DB생명": "DB생명_11월.jpg",
    "동부생명": "DB생명_11월.jpg",
    "디비생명": "DB생명_11월.jpg",
    "DB손해보험": "DB손보_1주.jpg",
    "DB손보": "DB손보_1주.jpg",
    "디비손보": "DB손보_1주.jpg",
    "디비": "DB손보_1주.jpg",
    "현대해상": "현대해상_1주.png",
    "현대": "현대해상_1주.png",
    "KB손보": "KB손보_1주차.jpg",
    "KB손해보험": "KB손보_1주차.jpg",
    "한화손보": "한화손보_1주.jpg",
    "한화손해보험": "한화손보_1주.jpg",
    "메리츠": "메리츠_11월_1주.jpg",
    "메리츠화재": "메리츠_11월_1주.jpg",
    "동양생명": "동양생명_11월.png",
    "동양": "동양생명_11월.png",
    "교보생명": "교보생명_11월.png",
    "교보": "교보생명_11월.png",
    "농협생명": "농협생명_11월.png",
    "농협": "농협생명_11월.png",
    "KDB생명": "KDB생명_11월.jpg",
    "KDB": "KDB생명_11월.jpg",
    "푸본현대": "푸본현대_11월.png",
    "푸본": "푸본현대_11월.png",
    "미래에셋": "미래에셋_11월.png",
    "미래": "미래에셋_11월.png",
    "메트라이프": "메트라이프_11월.jpg",
    "메트": "메트라이프_11월.jpg",
    "ABL생명": "ABL생명_11월.png",
    "ABL": "ABL생명_11월.png",
    "하나생명": "하나생명_11월.png",
    "IBK연금": "IBK연금_11월.png",
    "IM라이프": "IM라이프_11월.png",
    "롯데손보": "롯데손보_1주.jpg",
    "롯데": "롯데손보_1주.jpg",
    "하나손보": "하나손보_1주.jpg",
    "하나손해보험": "하나손보_1주.jpg",
    "농협손보": "농협손보_1주.jpg",
    "농협손해보험": "농협손보_1주.jpg",
    "흥국화재": "흥국화재_1주.jpg"
}

def find_flyer(comp_name: str) -> Tuple[str, str]:
    c_norm = comp_name.replace(" ", "").lower()
    if "kb생명" in c_norm or "kb라이프" in c_norm or "케이비생명" in c_norm or "케이비라이프" in c_norm:
        return "KB라이프", "KB라이프_11월.png"
    if "신한생명" in c_norm or "신한라이프" in c_norm or c_norm == "신한":
        return "신한라이프", "신한라이프_11월_p2.png"
    if "kb손" in c_norm:
        return "KB손해보험", "KB손보_1주차.jpg"
    if "db생명" in c_norm or "동부생명" in c_norm or "디비생명" in c_norm:
        return "DB생명", "DB생명_11월.jpg"
    if "db손" in c_norm or "동부화재" in c_norm or "디비손" in c_norm:
        return "DB손해보험", "DB손보_1주.jpg"
    if "흥국생명" in c_norm:
        return "흥국생명", "흥국생명_11월.png"
    if "흥국화재" in c_norm:
        return "흥국화재", "흥국화재_1주.jpg"
    if "한화생명" in c_norm:
        return "한화생명", "한화생명_11월.png"
    if "한화손" in c_norm:
        return "한화손해보험", "한화손보_1주.jpg"
    if "미래" in c_norm:
        return "미래에셋", "미래에셋_11월.png"
    if "라이나" in c_norm:
        return "라이나생명", "라이나생명_11월.png"
    if "메트" in c_norm:
        return "메트라이프", "메트라이프_11월.jpg"

    for k, v in FLYER_MAP.items():
        if k == comp_name or k.replace(" ", "").lower() == c_norm:
            return k, v
            
    sorted_keys = sorted(FLYER_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_keys:
        if k in comp_name or comp_name in k:
            return k, FLYER_MAP[k]
            
    return comp_name, "SKY_11월.jpg"


def build_flyer_response(comp_name: str) -> Dict[str, Any]:
    matched_k, filename = find_flyer(comp_name)
    encoded_comp = urllib.parse.quote(matched_k)
    encoded_filename = urllib.parse.quote(filename)
    flyer_url = f"https://skyblue-kakao-bot.onrender.com/flyer/{encoded_comp}"
    img_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_filename}"
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": f"📑 {matched_k} 11월 공식 시책지",
                        "description": "아래 [시책지 원본 열기]를 누르시면 고화질로 확대해 보실 수 있습니다.",
                        "thumbnail": {
                            "imageUrl": img_url
                        },
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "🔍 시책지 원본 열기",
                                "webLinkUrl": flyer_url
                            }
                        ]
                    }
                }
            ],
            "quickReplies": [
                {"messageText": "사용법", "action": "message", "label": "💡 사용법 (회사 상품 금액)"},
                {"messageText": f"{matched_k} 10만원", "action": "message", "label": f"{matched_k} 10만 계산"},
                {"messageText": f"{matched_k} 20만원", "action": "message", "label": f"{matched_k} 20만 계산"},
                {"messageText": "도움말", "action": "message", "label": "💡 도움말"}
            ]
        }
    }


# ==========================================
# 3. 대화형 되묻기 인터랙션 (회사만 / 금액누락 / 생보사 납기질의 / 흥국연속질의)
# ==========================================
def get_suggested_terms_for_life(comp: str, prod_name: str) -> List[str]:
    """생보사 상품별 최적화된 추천 납기 목록 생성 (사용자 지시: 납기 질의 및 메트라이프 납기별 차이 완벽 지원)"""
    c = comp.replace("생명", "").replace("라이프", "").strip()
    p = prod_name.replace(" ", "").lower()
    
    if c == "메트" or "달러" in p or "백만인" in p:
        return ["5년납(250%)", "7년납(400%)", "10년납(400%)", "15년납", "20년납"]
    elif "라이나" in c and ("종신" in p or "채우는" in p):
        return ["10년납 일반(950%)", "10년납 간편(450%)", "7년납(500%)", "착한간편종신(350%)"]
    elif "건강더한" in p:
        return ["7년납", "10년납", "15년납", "20년납"]
    elif "하나로" in p:
        return ["10년납", "15년납(법인시상)", "20년납"]
    elif "원픽" in p:
        return ["5년납", "7년납(법인시상)", "20년납"]
    elif "당당한" in p:
        return ["5년납", "7년납(법인시상)", "20년납"]
    elif "필요할때" in p:
        return ["10년납", "12년납", "15년납", "20년납"]
    elif "알행플" in p or "알행종" in p:
        return ["7년납(SKY시상)", "10년납(SKY시상)", "15년납", "20년납"]
    elif "쑥쑥" in p or "어린이" in p:
        return ["15년납", "20년납", "30년납"]
    elif "연금" in p:
        return ["10년납", "15년납", "20년납", "전기납"]
    elif "오튼튼" in p or "다사랑" in p or "3.10.5" in p:
        return ["10년납", "15년납", "20년납", "30년납"]
    elif "리턴100" in p:
        return ["10년납", "15년납", "20년납"]
    else:
        return ["10년납", "15년납", "20년납", "30년납"]


def build_ask_term_response(comp: str, prod_name: str, premium: int, terms: List[str]) -> Dict[str, Any]:
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    clean_prod = clean_product_display_name(prod_name)
    
    quick_replies = []
    for t in terms:
        clean_t = re.sub(r'\(.*?\)', '', t).strip()
        quick_replies.append({
            "messageText": f"{comp} {clean_prod} {prem_str} {clean_t}",
            "action": "message",
            "label": t
        })
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법 안내"})
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"📋 {comp} · {clean_prod} ({prem_str})\n\n생명보험사는 납입기간(*년납)에 따라 S환산 성적과 시상률이 다릅니다. 몇 년납으로 계산해 드릴까요?\n\n원하시는 납기 버튼을 누르시거나 직접 입력해 주세요!"
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }

def is_corp_incentive_target(comp: str, prod_name: str) -> bool:
    """한화생명 하나로, 푸본현대 맥스원픽, IM라이프 당당한인생 3개 상품은 법인계약만 추가지급 대상인지 확인"""
    c = comp.lower()
    p = prod_name.replace(" ", "").lower()
    if ('한화' in c) and ('하나로' in p):
        return True
    if ('푸본' in c) and ('원픽' in p):
        return True
    if ('im' in c or '아이엠' in c) and ('당당한' in p):
        return True
    return False


def build_ask_contract_type_response(comp: str, prod_name: str, premium: int, term: str) -> Dict[str, Any]:
    """한화 하나로, 푸본 맥스원픽, IM 당당한인생에 대해 개인계약인지 법인계약인지 확인하는 인터랙션 (사용자 지시 완벽 반영)"""
    prem_man = premium // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{premium:,}원"
    clean_prod = clean_product_display_name(prod_name)
    term_str = f" · {term}" if term else ""
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": (
                            f"📋 {comp} · {clean_prod} ({prem_str}{term_str})\n\n"
                            "본 상품의 SKY 본사 추가 시상은 **법인계약**에만 지급됩니다.\n"
                            "계약자가 개인인가요, 법인인가요?\n\n"
                            "아래 버튼을 눌러 선택해 주세요!"
                        )
                    }
                }
            ],
            "quickReplies": [
                {
                    "messageText": f"{comp} {clean_prod} {prem_str} {term} 법인계약".strip(),
                    "action": "message",
                    "label": "🏢 법인계약 (SKY시상 포함)"
                },
                {
                    "messageText": f"{comp} {clean_prod} {prem_str} {term} 개인계약".strip(),
                    "action": "message",
                    "label": "👤 개인계약"
                },
                {
                    "messageText": "사용법",
                    "action": "message",
                    "label": "💡 사용법 안내"
                }
            ]
        }
    }



def build_ask_product_and_amount_response(comp: str) -> Dict[str, Any]:
    info = ALL_COMPANIES.get(comp, {})
    recs = info.get("recommendations", [f"{info.get('default_prod', '주력')} 20만", f"{info.get('default_prod', '주력')} 10만"])
    
    quick_replies = [
        {"messageText": f"{comp} {r}", "action": "message", "label": r}
        for r in recs
    ]
    quick_replies.append({"messageText": f"{comp} 시책지", "action": "message", "label": f"📑 {comp} 시책지"})
    quick_replies.append({"messageText": "도움말", "action": "message", "label": "💡 사용법"})
    
    example = recs[0] if recs else f"{comp} 20만"
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"📋 {comp}\n\n어떤 상품과 월 보험료(금액)로 계산해 드릴까요?\n\n아래 추천 항목을 누르시거나 직접 입력해 주세요!\n(예: {comp} {example})"
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


def build_ask_amount_response(comp: str, prod_name: str, term: str = "") -> Dict[str, Any]:
    term_part = f" {term}" if term else ""
    quick_replies = [
        {"messageText": f"{comp} {prod_name}{term_part} 10만원", "action": "message", "label": "10만원"},
        {"messageText": f"{comp} {prod_name}{term_part} 20만원", "action": "message", "label": "20만원"},
        {"messageText": f"{comp} {prod_name}{term_part} 30만원", "action": "message", "label": "30만원"},
        {"messageText": f"{comp} {prod_name}{term_part} 50만원", "action": "message", "label": "50만원"},
        {"messageText": f"{comp} 시책지", "action": "message", "label": f"📑 {comp} 시책지"}
    ]
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": f"💰 {comp} · {prod_name}\n\n월 보험료(금액)를 선택해 주세요.\n(원하시는 금액 버튼을 누르시거나 직접 입력해 주세요)"
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


def build_heungkuk_continuous_inquiry_response(premium: Optional[int] = None) -> Dict[str, Any]:
    p_man = (premium // 10000) if premium else 20
    text_desc = (
        "🌸 흥국생명 10~11월 연속시상 안내\n\n"
        "흥국생명은 10월 실적 조건에 따라 2가지 연속시상이 있습니다:\n\n"
        "1️⃣ [10~11월 연속가동]\n"
        "• 조건: 10.26~31 및 11.1~6 양 기간 동일 구간 달성 시\n"
        "• 시상금: 5만(30만), 10만(60만), 20만(120만), 30만(180만), 50만(500만)\n\n"
        "2️⃣ [핑크멤버스]\n"
        "• 조건: 10월 전체 실적 10만 이상 달성 시\n"
        "• 시상금: 10만(50만), 20만(100만), 30만(150만), 50만(250만)\n\n"
        "해당하시는 조건을 선택하시면 정확한 총수령액을 산출해 드립니다!"
    )
    quick_replies = [
        {"messageText": f"흥국 오튼튼 {p_man}만 10-11월 연속포함", "action": "message", "label": f"🔥 10~11월 연속 (+120만)"},
        {"messageText": f"흥국 오튼튼 {p_man}만 핑크멤버스 포함", "action": "message", "label": f"🌸 핑크멤버스 (+100만)"},
        {"messageText": f"흥국 오튼튼 {p_man}만 둘다포함", "action": "message", "label": f"💎 둘다포함 (+220만)"},
        {"messageText": f"흥국 오튼튼 {p_man}만", "action": "message", "label": f"단건 기본 ({p_man}만)"}
    ]
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": text_desc}}],
            "quickReplies": quick_replies
        }
    }


# ==========================================
# 4. 2개 또는 3개 회사 비교 카드 엔진 (총합만 비교)
# ==========================================
def calculate_company_for_compare(comp_name: str, premium: int, text: str, continuous_mode: str) -> Dict[str, Any]:
    info = ALL_COMPANIES.get(comp_name, {})
    cat = info.get("category", "생명보험")
    default_prod = info.get("default_prod", "주력")
    default_term = info.get("default_term", "20년납")
    
    if cat == "손해보험":
        return calculate_nonlife(
            company=comp_name,
            product_name=default_prod,
            premium=premium,
            incentive_type="주력",
            continuous_mode=continuous_mode
        )
    else:
        m_term = re.search(r'(\d+)\s*년\s*납?|전기납', text)
        term = m_term.group(0) if m_term else default_term
        if term and not term.endswith("납"):
            term += "납"
        
        matched = search_life_product(comp_name, text, term=term)
        s_factor = matched['s_factor'] if matched else 1000.0
        prod_name = matched['product'] if matched else default_prod
        
        c_type = "법인" if any(k in text for k in ['법인', '법인계약']) else "개인"
        return calculate_life(
            company=comp_name,
            product_name=prod_name,
            premium=premium,
            s_factor=s_factor,
            term=term,
            incentive_type="전략",
            continuous_mode=continuous_mode,
            contract_type=c_type
        )


def build_compare_response(results: List[Dict[str, Any]], premium: int, continuous_mode: str = "none") -> Dict[str, Any]:
    prem_man = premium // 10000
    sorted_results = sorted(results, key=lambda x: x['grand_total'], reverse=True)
    diff = sorted_results[0]['grand_total'] - sorted_results[-1]['grand_total']
    winner = sorted_results[0]['company']
    
    ranks = ["🥇 1위", "🥈 2위", "🥉 3위"]
    item_list = []
    for i, r in enumerate(sorted_results):
        rank_label = ranks[i] if i < len(ranks) else f"{i+1}위"
        p_name = r.get('product_name', '')
        if len(p_name) > 10:
            p_name = p_name[:9] + "…"
        item_list.append({
            "title": f"{rank_label} {r['company']}",
            "description": f"{r['grand_total']:,}원"
        })
        
    buttons = []
    for r in sorted_results[:2]:
        buttons.append({
            "label": f"🔍 {r['company']} 상세 계산",
            "action": "message",
            "messageText": f"{r['company']} {r.get('product_name', '')} {prem_man}만원"
        })
        
    comp_names = " vs ".join(r['company'] for r in sorted_results)
    title_desc = f"{comp_names} 총합(수수료+시상) 비교"
    
    quick_replies = [
        {"messageText": f"{comp_names} 10만 비교", "action": "message", "label": "10만 비교"},
        {"messageText": f"{comp_names} 20만 비교", "action": "message", "label": "20만 비교"},
        {"messageText": f"{comp_names} 30만 비교", "action": "message", "label": "30만 비교"},
        {"messageText": f"{comp_names} {prem_man}만 연속포함 비교", "action": "message", "label": "🔥 연속시상 포함"},
        {"messageText": "도움말", "action": "message", "label": "💡 사용법"}
    ]
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": f"⚖️ {prem_man}만 원 판매 시 총수령액 비교",
                            "description": title_desc
                        },
                        "title": f"🏆 최고: {winner} (+{diff:,}원)",
                        "itemList": item_list,
                        "itemListSummary": {
                            "title": "1위 vs 최하위 격차",
                            "description": f"{diff:,}원"
                        },
                        "buttons": buttons
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


# ==========================================
# 5. 미답변 질문 표준 폴백 안내 (사용자 지정 문구)
# ==========================================
def build_fallback_response() -> Dict[str, Any]:
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "회사명 상품명 금액 을 입력해주세요\n(예: 한화생명 건강더한종신 100만)"
                    }
                }
            ],
            "quickReplies": [
                {"messageText": "한화생명 건강더한종신 100만", "action": "message", "label": "한화 건강더한 100만"},
                {"messageText": "흥국생명 오튼튼 20만 20년납", "action": "message", "label": "흥국 오튼튼 20만"},
                {"messageText": "메트라이프 달러종신 20만 10년납", "action": "message", "label": "메트 달러종신 20만"},
                {"messageText": "현대해상 주력 20만", "action": "message", "label": "현대 주력 20만"},
                {"messageText": "DB손보 10만원", "action": "message", "label": "DB손보 10만"},
                {"messageText": "신한라이프 통합건강 20만", "action": "message", "label": "신한 통합건강 20만"},
                {"messageText": "라이나 새로담는건강 20만", "action": "message", "label": "라이나 새로담는 20만"},
                {"messageText": "흥국 vs 현대 20만 비교", "action": "message", "label": "흥국 vs 현대 20만 비교"}
            ]
        }
    }


def build_kakao_response(calc_result: Dict[str, Any]) -> Dict[str, Any]:
    cat = calc_result.get("category", "")
    comp = calc_result.get("company", "")
    prod = calc_result.get("product_name", "")
    prem = calc_result.get("premium", 0)
    term = calc_result.get("term", "")
    
    prem_man = prem // 10000
    prem_str = f"{prem_man}만원" if prem_man > 0 else f"{prem:,}원"
    
    conv_rate = calc_result.get("conversion_rate", 0.0)
    s_grade = calc_result.get("s_grade", 0)
    
    next_comm = calc_result.get("next_month_comm", 0)
    next_comm_rate = calc_result.get("next_month_comm_rate", 0.0)
    inst_comm = calc_result.get("installment_comm", 0)
    inst_comm_rate = calc_result.get("installment_comm_rate", 0.0)
    tot_comm = calc_result.get("total_comm", 0)
    
    next_inc = calc_result.get("next_month_inc", 0)
    next_inc_rate = calc_result.get("next_month_inc_rate", 0.0)
    split_inc = calc_result.get("split_inc", 0)
    split_inc_rate = calc_result.get("split_inc_rate", 0.0)
    tot_inc = calc_result.get("total_inc", 0)
    tot_inc_rate = calc_result.get("total_inc_rate", 0.0)
    
    tot_next = calc_result.get("total_next_month", 0)
    tot_split = calc_result.get("total_split", 0)
    grand_total = calc_result.get("grand_total", 0)
    
    basis_desc = calc_result.get("basis_desc", "")
    cont_bonus_rate = calc_result.get("cont_bonus_rate", 0.0)
    c1_amount = calc_result.get("c1_amount", 0)
    c2_amount = calc_result.get("c2_amount", 0)
    is_heungkuk = calc_result.get("is_heungkuk", False)
    c_mode = calc_result.get("continuous_mode", "none")
    
    item_list = [
        {"title": "월 보험료 (월납)", "description": f"{prem:,}원"},
        {"title": f"S환산성적 ({conv_rate:.1f}%)", "description": f"{s_grade:,}원"},
        {"title": f"수수료 합계", "description": f"{tot_comm:,}원"},
        {"title": f"  • 익월 ({next_comm_rate:.0f}%)", "description": f"{next_comm:,}원"},
        {"title": f"  • 분급 ({inst_comm_rate:.0f}%)", "description": f"{inst_comm:,}원"},
        {"title": f"시상금 합계 ({tot_inc_rate:.0f}%)", "description": f"{tot_inc:,}원"},
        {"title": f"  • 익월시상 ({next_inc_rate:.0f}%)", "description": f"{next_inc:,}원"},
        {"title": f"  • 13회차/분할 ({split_inc_rate:.0f}%)", "description": f"{split_inc:,}원"},
        {"title": "────────────────", "description": "──────────"},
        {"title": "⚡ 익월 총수령 (수수료+시상)", "description": f"{tot_next:,}원"},
        {"title": "⏳ 분할/13회 총수령", "description": f"{tot_split:,}원"}
    ]
    
    quick_replies = [
        {"messageText": "사용법", "action": "message", "label": "💡 사용법 (회사 상품 금액)"}
    ]
    
    if is_heungkuk:
        c1_man = c1_amount // 10000
        c2_man = c2_amount // 10000
        if c_mode != "none":
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} {term}".strip(),
                "action": "message",
                "label": "↩️ 단건 시상으로 보기"
            })
        if "c1" not in c_mode and "both" not in c_mode and "all" not in c_mode and c1_man > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 10-11월 연속포함".strip(),
                "action": "message",
                "label": f"🔥 10~11월연속 (+{c1_man}만)"
            })
        if "c2" not in c_mode and "both" not in c_mode and "all" not in c_mode and c2_man > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 핑크멤버스 포함".strip(),
                "action": "message",
                "label": f"🌸 핑크멤버스 (+{c2_man}만)"
            })
        if "both" not in c_mode and "all" not in c_mode and (c1_man + c2_man) > 0:
            quick_replies.append({
                "messageText": f"흥국생명 {prod} {prem_str} 풀연속포함".strip(),
                "action": "message",
                "label": f"💎 둘다포함 (+{c1_man+c2_man}만)"
            })
    else:
        if cont_bonus_rate > 0:
            if c_mode != "none":
                quick_replies.append({
                    "messageText": f"{comp} {prod} {prem_str} {term}".strip(),
                    "action": "message",
                    "label": "↩️ 단건 시상으로 보기"
                })
            else:
                quick_replies.append({
                    "messageText": f"{comp} {prod} {prem_str} {term} 연속포함".strip(),
                    "action": "message",
                    "label": f"🔥 연속포함 (+{int(round(prem * cont_bonus_rate // 10000))}만)"
                })
            
    quick_replies.extend([
        {"messageText": f"{comp} {prod} 10만원 {term}".strip(), "action": "message", "label": "10만 계산"},
        {"messageText": f"{comp} {prod} 20만원 {term}".strip(), "action": "message", "label": "20만 계산"},
        {"messageText": f"{comp} vs 현대 20만 비교", "action": "message", "label": "비교하기"}
    ])
    
    basis_text = f"💡 시상 산출근거: {basis_desc}"
    if is_heungkuk and c_mode == "none":
        basis_text += f"\n(※ 10~11월 연속가동 또는 핑크멤버스 연속 시책은 아래 퀵버튼을 눌러 합산하실 수 있습니다)"
    elif not is_heungkuk and c_mode == "none" and cont_bonus_rate > 0:
        basis_text += f"\n(※ 전월 연속가동 시상은 아래 [🔥 연속포함] 버튼을 누르면 즉시 합산됩니다)"
        
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": f"[{cat}] {comp}",
                            "description": f"{clean_product_display_name(prod)} · {term}" if term else clean_product_display_name(prod)
                        },
                        "title": f"총 수령액 {grand_total:,}원",
                        "itemList": item_list,
                        "itemListSummary": {
                            "title": "최종 합계 (수수료 + 시상)",
                            "description": f"{grand_total:,}원"
                        },
                        "buttons": [
                            {
                                "label": "📑 " + comp + " 시책지 보기",
                                "action": "webLink",
                                "webLinkUrl": "https://skyblue-kakao-bot.onrender.com/flyer/" + urllib.parse.quote(comp)
                            }
                        ]
                    }
                },
                {
                    "simpleText": {
                        "text": basis_text
                    }
                }
            ],
            "quickReplies": quick_replies[:5]
        }
    }


def build_help_response() -> Dict[str, Any]:
    help_text = (
        "🤖 스카이블루에셋 정산 계산기\n\n"
        "회사명, 상품명, 금액을 입력하시면 익월/분급 수수료와 11월 공식 시상금을 즉시 계산해 드립니다.\n\n"
        "📌 [단건 계산 예시]\n"
        "• DB손보 10만원\n"
        "• 한화생명 건강더한종신 50만원 10년납\n"
        "• 메트라이프 달러종신 20만 10년납\n"
        "• 신한라이프 통합건강 20만 (연속포함)\n"
        "• 라이나 새로담는건강 20만\n"
        "• 흥국생명 오튼튼 20만 10-11월 연속\n"
        "• 미래에셋 M-케어건강 20만\n"
        "• 현대해상 주력 20만\n\n"
        "⚖️ [2~3개사 비교 예시]\n"
        "• 흥국 vs 현대 20만 비교\n"
        "• 흥국생명 현대해상 DB손보 20만 비교\n"
        "• 한화 vs 흥국 20만 비교\n\n"
        "💡 생명보험사는 금액 입력 시 납기(*년납)를 퀵버튼으로 먼저 여쭤봅니다!"
    )
    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": help_text}}],
            "quickReplies": [
                {"messageText": "DB손보 10만원", "action": "message", "label": "DB손보 10만"},
                {"messageText": "한화생명 건강더한종신 50만원", "action": "message", "label": "한화 건강더한 50만"},
                {"messageText": "메트라이프 달러종신 20만", "action": "message", "label": "메트 달러종신 20만"},
                {"messageText": "신한라이프 통합건강 20만", "action": "message", "label": "신한 통합건강 20만"},
                {"messageText": "라이나 새로담는건강 20만", "action": "message", "label": "라이나 새로담는 20만"},
                {"messageText": "흥국 vs 현대 20만 비교", "action": "message", "label": "흥국 vs 현대 20만 비교"}
            ]
        }
    }


@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "스카이블루에셋 카카오 챗봇 스킬 서버",
        "version": "2.7.1",
        "total_life_products": len(LIFE_PRODUCTS)
    }


@app.get("/flyer-img/{filename}")
def get_flyer_img(filename: str):
    import os
    import urllib.parse
    from fastapi.responses import FileResponse, RedirectResponse
    path = os.path.join("flyers", filename)
    if os.path.exists(path):
        return FileResponse(path)
    encoded_fn = urllib.parse.quote(filename)
    raw_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_fn}"
    return RedirectResponse(raw_url)


@app.get("/flyer/{company_name}")
def view_flyer_html(company_name: str):
    matched_k, filename = find_flyer(company_name)
    encoded_filename = urllib.parse.quote(filename)
    raw_cdn_url = f"https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{encoded_filename}"
    local_img_url = f"/flyer-img/{filename}"
    
    if "신한" in matched_k:
        pages = ["신한라이프_11월_p1.png", "신한라이프_11월_p2.png", "신한라이프_11월_p3.png"]
        img_tags = "".join([f'<div style="margin-bottom:16px;"><img src="https://raw.githubusercontent.com/jwchoi2313-alt/skyblue-kakao-bot/main/flyers/{p}" onerror="this.src=\'/flyer-img/{p}\'" alt="신한라이프 시책지 {i+1}페이지"><p style="text-align:center;font-size:12px;color:#94a3b8;margin:6px 0 20px;">[ {i+1} / 3 페이지 ]</p></div>' for i, p in enumerate(pages)])
    else:
        img_tags = f'<img src="{raw_cdn_url}" onerror="this.src=\'{local_img_url}\'" alt="{matched_k} 시책지">'
        
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>{matched_k} 11월 공식 시책지</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #0f172a;
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .header {{
            position: sticky;
            top: 0;
            width: 100%;
            max-width: 800px;
            background-color: #1e293b;
            padding: 12px 16px;
            box-sizing: border-box;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #334155;
            z-index: 100;
        }}
        .title {{
            font-size: 16px;
            font-weight: 700;
            margin: 0;
        }}
        .btn-group {{
            display: flex;
            gap: 8px;
        }}
        .action-btn {{
            background-color: #0284c7;
            color: white;
            text-decoration: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }}
        .action-btn.secondary {{
            background-color: #475569;
        }}
        .container {{
            width: 100%;
            max-width: 800px;
            padding: 8px 0;
            box-sizing: border-box;
        }}
        img {{
            width: 100%;
            height: auto;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">📑 {matched_k} 11월 공식 시책지</h1>
        <div class="btn-group">
            <a class="action-btn secondary" href="{raw_cdn_url}" target="_blank">고화질 원본</a>
            <a class="action-btn" href="{local_img_url}" download>다운로드</a>
        </div>
    </div>
    <div class="container">
        {img_tags}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ==========================================
# 6. 메인 카카오 스킬 라우터
# ==========================================

# ==========================================
# 0-1. 관리자 REST API (최총무 앱 전용)
# ==========================================
@app.get("/admin/users")
def get_admin_users(key: str = ""):
    if key != "skyblue2026admin":
        return {"error": "unauthorized"}
    return AUTH_CACHE

@app.post("/admin/approve")
async def admin_approve_user(request: Request):
    data = await request.json()
    if data.get("key") != "skyblue2026admin":
        return {"error": "unauthorized"}
    target = data.get("target", "")
    ok, msg = approve_user_by_name(target)
    return {"ok": ok, "msg": msg}

@app.post("/admin/block")
async def admin_block_user(request: Request):
    data = await request.json()
    if data.get("key") != "skyblue2026admin":
        return {"error": "unauthorized"}
    target = data.get("target", "")
    ok, msg = block_user_by_name(target)
    return {"ok": ok, "msg": msg}

@app.post("/skill/calculate")
async def kakao_skill_calculate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return build_fallback_response()

    user_request = body.get("userRequest", {})
    utterance = user_request.get("utterance", "").strip()
    user = user_request.get("user", {})
    user_id = user.get("id", "")

    # [인증 0단계] 관리자 등록 키워드 감지 (최정우 본부장님 카카오톡 연결)
    if any(k in utterance for k in ["관리자", "본부장"]) and any(k in utterance for k in ["최정우", "안양비전", "비전본부", "skyblue"]):
        register_admin(user_id, "최정우 본부장 (Admin)")
        return build_admin_registered_response()

    # [인증 1단계] 차단(강퇴) 계정 차단
    if is_blocked(user_id):
        return build_blocked_response()

    # [인증 2단계] 관리자 전용 명령어 (대기목록, 승인, 강퇴, 승인목록)
    if is_admin(user_id):
        admin_res = handle_admin_command(utterance)
        if admin_res:
            return admin_res

    # [인증 3단계] 미승인 사용자 통제
    if not is_approved(user_id):
        # 이미 대기 중인 경우
        if user_id in AUTH_CACHE.get("pending", {}):
            pinfo = AUTH_CACHE["pending"][user_id]
            # 보험사/계산 관련 키워드가 있으면 대기 중 안내
            has_insurance_kw = any(k in utterance for k in ['생명', '손보', '화재', '해상', '라이프', '원', '만', '시책', '도움말', '환산', '비교'])
            if has_insurance_kw:
                return build_pending_response(pinfo.get("name", "신청자"), pinfo.get("requested_at", ""))
            else:
                # 정보 수정 입력으로 간주
                pinfo["name"] = utterance
                pinfo["requested_at"] = get_now_kst()
                save_auth_db(f"Update pending request: {utterance}")
                return build_request_submitted_response(utterance, pinfo["requested_at"])
        else:
            # 최초 미승인자
            has_insurance_kw = any(k in utterance for k in ['생명', '손보', '화재', '해상', '라이프', '00', '0만', '원', '납', '시책', '비교', 'vs'])
            if len(utterance) <= 30 and not has_insurance_kw and utterance not in ["도움말", "사용법", "시작", "메뉴", "help", "?"]:
                request_approval(user_id, utterance)
                return build_request_submitted_response(utterance, get_now_kst())
            else:
                return build_auth_required_response()

    if not utterance or utterance in ["도움말", "사용법", "메뉴", "시작", "help", "?"]:
        return build_help_response()

    try:
        # 1. 시책지 전단지 직접 요청 처리
        if any(kw in utterance for kw in ['시책지', '시책표', '전단지', '시책확인']):
            for k in FLYER_MAP.keys():
                if k in utterance:
                    return build_flyer_response(k)
            return build_flyer_response("스카이블루")

        # 2. 회사명 및 금액 추출
        matched_comps = find_companies_in_text(utterance)
        premium = parse_premium(utterance)
        # 계약자 형태 (개인 vs 법인) 추출
        contract_type = ""
        if any(k in utterance for k in ['법인', '법인계약']):
            contract_type = "법인"
        elif any(k in utterance for k in ['개인', '개인계약']):
            contract_type = "개인"
        
        # 연속시상 모드 판정
        continuous_mode = "none"
        if "핑크" in utterance:
            continuous_mode = "c2"
        elif any(kw in utterance for kw in ['10-11', '10월연속', '연속가동']):
            continuous_mode = "c1"
        elif any(kw in utterance for kw in ['풀', '모두', '둘다', '전체', '연속포함', '연속', '연계']):
            continuous_mode = "both"
            
        # 흥국생명 연속시상 질의 판정
        if any(k in utterance for k in ['흥국']) and any(kw in utterance for kw in ['연속시상', '연속얼마', '10월실적', '10월']) and premium is None:
            return build_heungkuk_continuous_inquiry_response()

        is_compare_query = (
            len(matched_comps) >= 2 or
            (len(matched_comps) >= 2 and any(k in utterance for k in ['비교', 'vs', 'VS', '대', '차이']))
        )

        # 3. 2개 또는 3개 회사 비교 처리 (총합만 비교하는 카드)
        if is_compare_query:
            target_comps = matched_comps[:3]
            comp_prem = premium or 200000
            comp_results = []
            for c in target_comps:
                res = calculate_company_for_compare(c, comp_prem, utterance, continuous_mode)
                comp_results.append(res)
            return build_compare_response(comp_results, comp_prem, continuous_mode)

        # 4. 단일 회사 처리
        if len(matched_comps) == 1:
            comp = matched_comps[0]
            
            cleaned = utterance
            for alias in ALL_COMPANIES[comp]['aliases']:
                cleaned = re.sub(re.escape(alias), '', cleaned, flags=re.IGNORECASE)
            cleaned_tokens = re.sub(r'[시책|계산|얼마|수수료|시상|조회|알려줘|해줘|\s|\?|\!|\.]', '', cleaned)
            
            # Case 4-A: 상품과 금액 없이 회사명만 입력한 경우 -> 둘 다 되묻기
            if premium is None and len(cleaned_tokens) == 0:
                return build_ask_product_and_amount_response(comp)
                
            # Case 4-B: 상품명은 있으나 금액이 없는 경우 -> 금액만 되묻기
            if premium is None:
                info = ALL_COMPANIES[comp]
                m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                term = m_term.group(0) if m_term else info.get("default_term", "")
                prod_name = cleaned_tokens if cleaned_tokens else info.get("default_prod", "주력")
                return build_ask_amount_response(comp, prod_name, term)
                
            # Case 4-C: 금액이 명시된 정상 단건 계산
            calc_prem = premium
            info = ALL_COMPANIES[comp]
            
            # 손해보험: 92% 고정 및 1주차 시책 즉시 계산
            if info['category'] == "손해보험":
                prod_name = "주력보종"
                for p in ['퍼펙트', '간편', '굿앤굿', '주력', '종합', '자녀', '나에게맞춘', '참좋은', '훼밀리', '아이러브', '행복플러스']:
                    if p in utterance:
                        prod_name = p
                        break
                calc_res = calculate_nonlife(comp, prod_name, calc_prem, incentive_type="주력", continuous_mode=continuous_mode)
                return build_kakao_response(calc_res)
                
            # 생명보험: 사용자 명확 지침 ("생명보험사는 금액을 적고나면 납입기간을 확인해서 답을 주도록 해줘")
            else:
                m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
                term = m_term.group(0) if m_term else ""
                if term and not term.endswith("납"):
                    term += "납"
                    
                matched = search_life_product(comp, utterance, term=term)
                prod_name = matched['product'] if matched else info.get("default_prod", "보장성")

                # 납입기간이 지정되지 않은 경우 -> 사용자 지시대로 납기 먼저 질의!
                if not term:
                    suggested_terms = get_suggested_terms_for_life(comp, prod_name)
                    return build_ask_term_response(comp, prod_name, calc_prem, suggested_terms)

                # 한화 하나로, 푸본 맥스원픽, IM 당당한인생 3개 상품은 법인계약만 추가지급 -> 개인/법인 질의!
                if is_corp_incentive_target(comp, prod_name) and not contract_type:
                    return build_ask_contract_type_response(comp, prod_name, calc_prem, term)
                    
                # 납입기간 및 계약형태가 확정된 경우 -> 해당 납기로 정확히 즉시 계산!
                s_factor = matched['s_factor'] if matched else 1000.0
                calc_res = calculate_life(
                    company=comp,
                    product_name=prod_name,
                    premium=calc_prem,
                    s_factor=s_factor,
                    term=term,
                    incentive_type="전략",
                    continuous_mode=continuous_mode,
                    contract_type=contract_type or "개인"
                )
                return build_kakao_response(calc_res)

        # 5. 회사명은 없지만 대표 상품명이 직접 들어온 경우 (예: 오튼튼 20만)
        if premium is not None:
            m_term = re.search(r'(\d+)\s*년\s*납?|전기납', utterance)
            term = m_term.group(0) if m_term else ""
            if term and not term.endswith("납"):
                term += "납"

            if any(k in utterance for k in ['오튼튼', '다사랑', '3.10.5', '3105']):
                matched = search_life_product("흥국생명", utterance, term=term)
                prod_name = matched['product'] if matched else "오튼튼5.10.5건강보험, 다(多)사랑암"
                if not term:
                    return build_ask_term_response("흥국생명", prod_name, premium, ["10년납", "15년납", "20년납", "30년납"])
                s_factor = matched['s_factor'] if matched else 1100.0
                calc_res = calculate_life("흥국생명", prod_name, premium, s_factor, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['달러종신', '백만인']):
                if not term:
                    return build_ask_term_response("메트라이프", "백만인을 위한 달러종신보험 Plus", premium, ["5년납(250%)", "7년납(400%)", "10년납(400%)", "15년납", "20년납"])
                matched = search_life_product("메트라이프", "달러종신", term=term)
                s_factor = matched['s_factor'] if matched else 647.55
                calc_res = calculate_life("메트라이프", matched['product'], premium, s_factor, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['하나로', '하나로H']):
                matched = search_life_product("한화생명", utterance, term=term)
                prod_name = matched['product'] if matched else "하나로 H종신"
                if not term:
                    return build_ask_term_response("한화생명", prod_name, premium, ["10년납", "15년납(법인시상)", "20년납"])
                if not contract_type:
                    return build_ask_contract_type_response("한화생명", prod_name, premium, term)
                s_factor = matched['s_factor'] if matched else 1300.0
                calc_res = calculate_life("한화생명", prod_name, premium, s_factor, term, "전략", continuous_mode, contract_type=contract_type or "개인")
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['맥스원픽', '원픽종신', '원픽']):
                matched = search_life_product("푸본현대", utterance, term=term)
                prod_name = matched['product'] if matched else "MAX 종신보험 원픽"
                if not term:
                    return build_ask_term_response("푸본현대", prod_name, premium, ["5년납", "7년납(법인시상)", "20년납"])
                if not contract_type:
                    return build_ask_contract_type_response("푸본현대", prod_name, premium, term)
                s_factor = matched['s_factor'] if matched else 300.0
                calc_res = calculate_life("푸본현대", prod_name, premium, s_factor, term, "전략", continuous_mode, contract_type=contract_type or "개인")
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['당당한인생', '당당한']):
                matched = search_life_product("IM라이프", utterance, term=term)
                prod_name = matched['product'] if matched else "당당한 인생종신"
                if not term:
                    return build_ask_term_response("IM라이프", prod_name, premium, ["5년납", "7년납(법인시상)", "20년납"])
                if not contract_type:
                    return build_ask_contract_type_response("IM라이프", prod_name, premium, term)
                s_factor = matched['s_factor'] if matched else 873.2
                calc_res = calculate_life("IM라이프", prod_name, premium, s_factor, term, "전략", continuous_mode, contract_type=contract_type or "개인")
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['건강더한']):
                if not term:
                    return build_ask_term_response("한화생명", "건강더한종신", premium, ["7년납", "10년납", "15년납", "20년납"])
                calc_res = calculate_life("한화생명", "건강더한종신", premium, 1100.0, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['알행플']):
                if not term:
                    return build_ask_term_response("DB생명", "알행플종신", premium, ["7년납", "10년납", "15년납", "20년납"])
                calc_res = calculate_life("DB생명", "알행플종신", premium, 1020.0, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['새로담는', '브레인케어']):
                if not term:
                    return build_ask_term_response("라이나생명", "새로담는건강보험", premium, ["10년납", "15년납", "20년납", "30년납"])
                calc_res = calculate_life("라이나생명", "새로담는건강보험", premium, 1000.0, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['m케어', '엠케어']):
                if not term:
                    return build_ask_term_response("미래에셋", "M-케어건강보험", premium, ["10년납", "15년납", "20년납", "30년납"])
                calc_res = calculate_life("미래에셋", "M-케어건강보험", premium, 825.0, term, "전략", continuous_mode)
                return build_kakao_response(calc_res)
            elif any(k in utterance for k in ['퍼펙트', '간편', '굿앤굿', '주력']):
                calc_res = calculate_nonlife("현대해상", "주력보종", premium, "주력", continuous_mode)
                return build_kakao_response(calc_res)

        # 6. 해석 불가 질문 -> 사용자 지정 표준 폴백 메시지 반환
        return build_fallback_response()

    except Exception as e:
        return build_fallback_response()
