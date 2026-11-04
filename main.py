import os
import sys
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

EMBEDDED_LIFE_DATA = '[{"company":"한화","product":"제로백H종신","term":"10년납","gubun":"일반가입","s_factor":1140.0},{"company":"한화","product":"제로백H종신","term":"20년납 이상","gubun":"","s_factor":1425.0},{"company":"한화","product":"제로백H종신","term":"10년납","gubun":"간편가입","s_factor":1092.5},{"company":"한화","product":"제로백H종신","term":"20년납 이상","gubun":"","s_factor":1377.5},{"company":"한화","product":"H 종신","term":"5년납","gubun":"일반가입","s_factor":605.0},{"company":"한화","product":"H 종신","term":"7년납","gubun":"","s_factor":880.0000000000001},{"company":"한화","product":"H 종신","term":"5년납","gubun":"간편가입","s_factor":550.0},{"company":"한화","product":"H 종신","term":"7년납","gubun":"","s_factor":825.0000000000001},{"company":"한화","product":"밸류플러스보장보험2.0","term":"5년납","gubun":"일반가입","s_factor":605.0},{"company":"한화","product":"밸류플러스보장보험2.0","term":"7년납","gubun":"","s_factor":880.0000000000001},{"company":"한화","product":"밸류플러스보장보험2.0","term":"10년납","gubun":"","s_factor":1100.0},{"company":"한화","product":"밸류플러스보장보험2.0","term":"5년납","gubun":"간편가입","s_factor":550.0},{"company":"한화","product":"밸류플러스보장보험2.0","term":"7년납","gubun":"","s_factor":825.0000000000001},{"company":"한화","product":"밸류플러스보장보험2.0","term":"10년납","gubun":"","s_factor":1100.0},{"company":"한화","product":"건강더한종신","term":"7년납","gubun":"일반가입","s_factor":880.0000000000001},{"company":"한화","product":"건강더한종신","term":"10년납","gubun":"","s_factor":1100.0},{"company":"한화","product":"건강더한종신","term":"7년납","gubun":"간편가입","s_factor":825.0000000000001},{"company":"한화","product":"건강더한종신","term":"10년납","gubun":"","s_factor":1100.0},{"company":"한화","product":"필요할때쓰는종신","term":"10년납","gubun":"일반,간편","s_factor":1100.0},{"company":"한화","product":"필요할때쓰는종신","term":"12년납","gubun":"","s_factor":1210.0},{"company":"한화","product":"(간편)경영인H정기","term":"전기납","gubun":"","s_factor":1800.0},{"company":"한화","product":"상속H종신보험","term":"10년납","gubun":"일반가입","s_factor":1100.0},{"company":"한화","product":"상속H종신보험","term":"15년납","gubun":"","s_factor":1500.0},{"company":"한화","product":"상속H종신보험","term":"20년납 이상","gubun":"","s_factor":1700.0},{"company":"한화","product":"상속H종신보험","term":"10년납","gubun":"간편가입","s_factor":1000.0},{"company":"한화","product":"상속H종신보험","term":"15년납","gubun":"","s_factor":1400.0},{"company":"한화","product":"상속H종신보험","term":"20년납 이상","gubun":"","s_factor":1600.0},{"company":"한화","product":"하나로 H종신","term":"10년납","gubun":"일반가입 간편가입","s_factor":1000.0},{"company":"한화","product":"하나로 H종신","term":"15년납","gubun":"","s_factor":1300.0},{"company":"한화","product":"하나로 H종신","term":"20년납 이상","gubun":"","s_factor":1500.0},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)","term":"7년납","gubun":"일반심사형 간편심사형","s_factor":846.0},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)","term":"10년납","gubun":"","s_factor":1020.0},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (기본형)","term":"20년납↑","gubun":"","s_factor":1800.0},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)","term":"7년납","gubun":"일반심사형 간편심사형","s_factor":902.4},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)","term":"10년납","gubun":"","s_factor":1080.0},{"company":"DB","product":"백년친구 뉴-알행플종신 (해지환급금일부지급형) (체증형)","term":"20년납↑","gubun":"","s_factor":1860.0},{"company":"DB","product":"알차고 행복한 리턴 종신 (해약환급금 일부지급형)","term":"5년납","gubun":"일반심사형 간편심사형","s_factor":789.6000000000001},{"company":"DB","product":"알차고 행복한 리턴 종신 (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":846.0},{"company":"DB","product":"알차고 행복한 리턴 종신 (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":1020.0000000000002},{"company":"DB","product":"알차고 행복한 리턴 종신 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":1380.0},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"5년납","gubun":"일반","s_factor":655.1999999999999},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"7년납","gubun":"","s_factor":856.8},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"10년납","gubun":"","s_factor":1108.8},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"12년납","gubun":"","s_factor":1209.6},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"15년납","gubun":"","s_factor":1461.6},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"20년납↑","gubun":"","s_factor":2100.0},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"5년납","gubun":"간편","s_factor":705.6},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"7년납","gubun":"","s_factor":806.4},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"10년납","gubun":"","s_factor":1209.6},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"12년납","gubun":"","s_factor":1310.3999999999999},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"15년납","gubun":"","s_factor":1512.0},{"company":"DB","product":"10년더드림플러스유니버셜종신 (보증비용부과형) (100%형)(해지환급금보증형)","term":"20년납↑","gubun":"","s_factor":2100.0},{"company":"DB","product":"뉴-올케어 암종신 (해약환급금 일부지급형)","term":"10년납","gubun":"일반,간편","s_factor":806.4},{"company":"DB","product":"뉴-올케어 암종신 (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":1159.2},{"company":"DB","product":"뉴-올케어 암종신 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":1562.3999999999999},{"company":"DB","product":"(간편한)경영인 정기(2501) (해약환급금 일부지급형)","term":"1형 (5%체증형)","gubun":"","s_factor":1702.8},{"company":"DB","product":"(간편한)경영인 정기(2501) (해약환급금 일부지급형)","term":"2형 (10%체증형)","gubun":"","s_factor":1702.8},{"company":"신한","product":"종신보험 세븐Plus골드","term":"20년납","gubun":"일반,간편","s_factor":1120.0},{"company":"신한","product":"종신보험 세븐PlusⅡ","term":"20년납","gubun":"일반,간편","s_factor":1400.0},{"company":"신한","product":"신한모아더드림종신 (해약환급금 일부지급형)","term":"5년납이상","gubun":"일반심사 간편심사","s_factor":481.0},{"company":"신한","product":"신한모아더드림종신 (해약환급금 일부지급형)","term":"7년납이상","gubun":"","s_factor":663.0},{"company":"신한","product":"신한모아더드림Plus종신 (해약환급금 일부지급형)","term":"5년납","gubun":"일반심사 간편심사","s_factor":420.0},{"company":"신한","product":"신한모아더드림Plus종신 (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":735.0},{"company":"신한","product":"신한모아더드림Plus종신 (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":840.0},{"company":"신한","product":"(간편가입)종신보험 세븐Plus","term":"20년납","gubun":"","s_factor":1100.0},{"company":"신한","product":"위너스경영인정기 (체증형)","term":"20년납이상","gubun":"일반심사형","s_factor":1400.0},{"company":"신한","product":"든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)","term":"5년납","gubun":"일반심사 간편심사","s_factor":450.0},{"company":"신한","product":"든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)","term":"7년납","gubun":"","s_factor":600.0},{"company":"신한","product":"든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)","term":"10년납","gubun":"","s_factor":900.0},{"company":"신한","product":"든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)","term":"15년납","gubun":"","s_factor":1200.0},{"company":"신한","product":"든든한실속(간편)종신, 든든한VIP상속(간편)종신:1억이상 (해약환급금 미지급형)","term":"20년납","gubun":"","s_factor":1455.0},{"company":"신한","product":"The든든한종신보험","term":"10년납","gubun":"일반심사 간편심사","s_factor":900.0},{"company":"신한","product":"The든든한종신보험","term":"15년납","gubun":"","s_factor":1200.0},{"company":"신한","product":"The든든한종신보험","term":"20년납","gubun":"","s_factor":1455.0},{"company":"신한","product":"(간편가입)리필종신","term":"10년납","gubun":"기본납입형","s_factor":630.0},{"company":"신한","product":"(간편가입)리필종신","term":"20년납","gubun":"","s_factor":840.0},{"company":"신한","product":"(간편가입)리필종신","term":"10년납","gubun":"집중납입형","s_factor":420.0},{"company":"신한","product":"(간편가입)리필종신","term":"20년납","gubun":"","s_factor":570.0},{"company":"신한","product":"3케어리워드종신","term":"10년납","gubun":"일반,간편","s_factor":630.0},{"company":"신한","product":"3케어리워드종신","term":"20년납","gubun":"","s_factor":840.0},{"company":"신한","product":"통합건강보장 슈퍼원(ONE)","term":"10년납이상","gubun":"","s_factor":675.0},{"company":"신한","product":"통합건강보장 슈퍼원(ONE)","term":"15년납이상","gubun":"","s_factor":855.0},{"company":"신한","product":"통합건강보장 슈퍼원(ONE)","term":"20년납이상","gubun":"","s_factor":990.0},{"company":"신한","product":"통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)","term":"10년납","gubun":"일반심사 간편심사","s_factor":720.0},{"company":"신한","product":"통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)","term":"15년납","gubun":"","s_factor":900.0},{"company":"신한","product":"통합건강보장보험원(ONE), 통합건강보장라이트원(ONE),  (3.10.5고당지알파)","term":"20년납이상","gubun":"","s_factor":1080.0},{"company":"신한","product":"통합건강보험 원(ONE) 갱신형","term":"10년납이상","gubun":"일반,간편","s_factor":720.0},{"company":"신한","product":"통합건강보험 원(ONE) 갱신형","term":"20년납이상","gubun":"","s_factor":1080.0},{"company":"신한","product":"신한ONE더라이프 연금","term":"5년납이상","gubun":"연금액 보증형","s_factor":50.0},{"company":"신한","product":"신한ONE더라이프 연금","term":"7년납이상","gubun":"","s_factor":250.0},{"company":"신한","product":"신한ONE더라이프 연금","term":"10년납이상","gubun":"","s_factor":550.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"5년납","gubun":"기본형","s_factor":130.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"7년납","gubun":"","s_factor":300.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"10년납이상","gubun":"","s_factor":420.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"5년납","gubun":"연금 강화형","s_factor":170.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"7년납","gubun":"","s_factor":340.0},{"company":"신한","product":"신한ONE더드림 변액연금","term":"10년납이상","gubun":"","s_factor":560.0},{"company":"KB","product":"7년의약속 플러스 평생종신","term":"20년납","gubun":"-","s_factor":786.0},{"company":"KB","product":"KB 약속플러스종신 (해약환급금일부지급형)","term":"5년납","gubun":"","s_factor":414.09999999999997},{"company":"KB","product":"KB 약속플러스종신 (해약환급금일부지급형)","term":"7년납","gubun":"","s_factor":479.7},{"company":"KB","product":"KB 약속플러스종신 (해약환급금일부지급형)","term":"10년납","gubun":"","s_factor":561.6999999999999},{"company":"KB","product":"KB 리턴종신 (해약환급금 일부지급형)","term":"5년납","gubun":"보증비용 부과형","s_factor":738.0},{"company":"KB","product":"KB 리턴종신 (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":762.5999999999999},{"company":"KB","product":"KB 리턴종신 (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":861.0},{"company":"KB","product":"KB 리턴종신 (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":889.6999999999999},{"company":"KB","product":"KB 리턴종신 (해약환급금 일부지급형)","term":"20년납 이상","gubun":"","s_factor":1025.0},{"company":"KB","product":"경영인 정기보험Ⅲ","term":"20년납 이상","gubun":"","s_factor":1348.8999999999999},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"5년납","gubun":"계약자 적립액 보증형","s_factor":250.1},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"7년납","gubun":"","s_factor":410.0},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"10년납","gubun":"","s_factor":684.6999999999999},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"5년납","gubun":"계약자 적립액 미보증형","s_factor":164.0},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"7년납","gubun":"","s_factor":225.5},{"company":"KB","product":"KB 트리플 레벨업 연금보험","term":"10년납","gubun":"","s_factor":262.4},{"company":"KB","product":"KB넥스트레벨업연금보험","term":"10년납","gubun":"보증형","s_factor":635.5},{"company":"KB","product":"KB넥스트레벨업연금보험","term":"12년납","gubun":"","s_factor":684.6999999999999},{"company":"KB","product":"KB넥스트레벨업연금보험","term":"10년납","gubun":"미보증형","s_factor":262.4},{"company":"KB","product":"KB넥스트레벨업연금보험","term":"12년납","gubun":"","s_factor":303.4},{"company":"KB","product":"100세든든 연금보험(기본형)","term":"10년납이상","gubun":"","s_factor":402.0},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"10년납","gubun":"해약환급금 미지급형","s_factor":491.99999999999994},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"15년납","gubun":"","s_factor":758.5},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"20년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"30년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"10년납","gubun":"갱신형","s_factor":491.99999999999994},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"20년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"딱좋은 0540 건강보험 (해약환급금 미지급형), 3.N.5 딱좋은 요즘 건강보험","term":"30년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험","term":"10년납","gubun":"해약환급금 미지급형","s_factor":491.99999999999994},{"company":"KB","product":"5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험","term":"15년납","gubun":"","s_factor":758.5},{"company":"KB","product":"5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험","term":"20년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"5.10.5 딱좋은 플러스 건강보험 3.10.5 딱좋은 초경증 건강보험","term":"30년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)","term":"10년납","gubun":"","s_factor":902.0},{"company":"KB","product":"행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)","term":"15년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)","term":"20년납","gubun":"","s_factor":1127.5},{"company":"KB","product":"행복한약속 치매간병 (해약환급금 일부지급형) (주계약기준)","term":"30년납","gubun":"","s_factor":1148.0},{"company":"KB","product":"골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)","term":"10년납","gubun":"","s_factor":491.99999999999994},{"company":"KB","product":"골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)","term":"15년납","gubun":"","s_factor":758.5},{"company":"KB","product":"골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)","term":"20년납","gubun":"","s_factor":1025.0},{"company":"KB","product":"골든라이프 딱좋은 간병보험 무배당 (해약환급금 미지급형)","term":"30년납","gubun":"","s_factor":1025.0},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"20년납","gubun":"일반가입","s_factor":1391.8500000000001},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"15년납","gubun":"","s_factor":1246.05},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"10년납","gubun":"","s_factor":647.5500000000001},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"7년납","gubun":"","s_factor":540.9},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"5년납","gubun":"","s_factor":305.1},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"20년납","gubun":"간편가입","s_factor":1156.05},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"15년납","gubun":"","s_factor":1156.05},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"10년납","gubun":"","s_factor":497.7},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"7년납","gubun":"","s_factor":540.9},{"company":"메트","product":"백만인을 위한 달러종신보험 Plus (저해약환급금형) 가입금액: 2만달러 이상","term":"5년납","gubun":"","s_factor":266.40000000000003},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"20년납","gubun":"일반가입","s_factor":1391.8500000000001},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"15년납","gubun":"","s_factor":1246.05},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"10년납","gubun":"","s_factor":647.5500000000001},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"7년납","gubun":"","s_factor":459.0},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"5년납","gubun":"","s_factor":227.70000000000002},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"20년납","gubun":"간편가입","s_factor":1117.8},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"15년납","gubun":"","s_factor":1117.8},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"10년납","gubun":"","s_factor":459.0},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"7년납","gubun":"","s_factor":305.1},{"company":"메트","product":"백만인을 위한  종신보험 Plus (저해약환급금형) 가입금액: 2천만 이상","term":"5년납","gubun":"","s_factor":189.45000000000002},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"25년납이상","gubun":"3천만 이상","s_factor":1775.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"20년납이상","gubun":"","s_factor":1775.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"15년납이상","gubun":"","s_factor":1775.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"10년납이상","gubun":"","s_factor":1435.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"9년납이하","gubun":"","s_factor":1191.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"7년납이하","gubun":"","s_factor":915.5},{"company":"메트","product":"오늘의종신Plus / VIP Plus","term":"5년납이하","gubun":"","s_factor":764.5},{"company":"메트","product":"360 종합보장보험","term":"20년납이상","gubun":"일반가입 간편가입","s_factor":1597.95},{"company":"메트","product":"360 종합보장보험","term":"19년납이하","gubun":"","s_factor":1541.7},{"company":"메트","product":"360 종합보장보험","term":"14년납이하","gubun":"","s_factor":1156.05},{"company":"메트","product":"360 암보험 (갱신형)","term":"전기납","gubun":"일반가입","s_factor":1597.95},{"company":"메트","product":"간편 360 종합보장보험 (갱신형)","term":"전기납","gubun":"간편가입","s_factor":1442.7},{"company":"농협","product":"마이초이스NH종신보험","term":"5년","gubun":"해지환급금 일부지급형","s_factor":510.0},{"company":"농협","product":"마이초이스NH종신보험","term":"7년","gubun":"","s_factor":810.0},{"company":"농협","product":"마이초이스NH종신보험","term":"10년","gubun":"","s_factor":990.0},{"company":"농협","product":"마이초이스NH종신보험","term":"12년","gubun":"","s_factor":1080.0},{"company":"농협","product":"마이초이스NH종신보험","term":"5년","gubun":"표준형","s_factor":390.0},{"company":"농협","product":"마이초이스NH종신보험","term":"7년","gubun":"","s_factor":540.0},{"company":"농협","product":"마이초이스NH종신보험","term":"10년","gubun":"","s_factor":750.0},{"company":"농협","product":"마이초이스NH종신보험","term":"12년","gubun":"","s_factor":870.0},{"company":"농협","product":"마이초이스NH종신보험","term":"20년","gubun":"","s_factor":1440.0},{"company":"농협","product":"투스텝NH종신","term":"10년","gubun":"해약환급금일부지급형","s_factor":480.0},{"company":"농협","product":"투스텝NH종신","term":"12년","gubun":"","s_factor":630.0},{"company":"농협","product":"건강채움NH암종신보험 (해약환급금일부지급형)","term":"10년","gubun":"스마트 페이형","s_factor":450.0},{"company":"농협","product":"건강채움NH암종신보험 (해약환급금일부지급형)","term":"15년","gubun":"","s_factor":720.0},{"company":"농협","product":"건강채움NH암종신보험 (해약환급금일부지급형)","term":"10년","gubun":"일반페이형","s_factor":690.0},{"company":"농협","product":"건강채움NH암종신보험 (해약환급금일부지급형)","term":"15년","gubun":"","s_factor":1020.0},{"company":"농협","product":"스텝업700NH종신보험","term":"해약환급금일부지급형","gubun":"","s_factor":1397.5},{"company":"농협","product":"행복한NH경영인정기","term":"해약환급금일부지급형","gubun":"","s_factor":1350.0},{"company":"농협","product":"행복한NH경영인정기","term":"표준형","gubun":"","s_factor":625.0},{"company":"농협","product":"NH올원더풀기억안심치매보험 (주계약기준)","term":"10년이상","gubun":"해약환급금 일부지급형","s_factor":550.0},{"company":"농협","product":"NH올원더풀기억안심치매보험 (주계약기준)","term":"15년이상","gubun":"","s_factor":775.0},{"company":"농협","product":"NH올원더풀기억안심치매보험 (주계약기준)","term":"20년이상","gubun":"","s_factor":975.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"10년이상","gubun":"해약환급금 미지급형","s_factor":450.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"15년이상","gubun":"","s_factor":650.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"20년이상","gubun":"","s_factor":850.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"30년이상","gubun":"","s_factor":1100.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"10년이상","gubun":"표준형","s_factor":400.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"15년이상","gubun":"","s_factor":525.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"20년이상","gubun":"","s_factor":650.0},{"company":"농협","product":"NH올원더풀간병안심요양보험 (주계약기준)","term":"30년이상","gubun":"","s_factor":875.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"10년미만","gubun":"간편가입","s_factor":250.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"10년이상","gubun":"","s_factor":450.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"15년이상","gubun":"","s_factor":650.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"20년이상","gubun":"","s_factor":800.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"10년미만","gubun":"일반가입","s_factor":225.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"10년이상","gubun":"","s_factor":425.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"15년이상","gubun":"","s_factor":600.0},{"company":"농협","product":"핑크케어 NH건강보험","term":"20년이상","gubun":"","s_factor":750.0},{"company":"농협","product":"건강플러스NH통합보험","term":"10년이상","gubun":"해지환급금 미지급형","s_factor":475.0},{"company":"농협","product":"건강플러스NH통합보험","term":"15년이상","gubun":"","s_factor":650.0},{"company":"농협","product":"건강플러스NH통합보험","term":"20년이상","gubun":"","s_factor":775.0},{"company":"농협","product":"건강플러스NH통합보험","term":"10년이상","gubun":"표준형","s_factor":375.0},{"company":"농협","product":"건강플러스NH통합보험","term":"15년이상","gubun":"","s_factor":500.0},{"company":"농협","product":"건강플러스NH통합보험","term":"20년이상","gubun":"","s_factor":625.0},{"company":"농협","product":"치료비안심해2NH건강보험","term":"10년미만","gubun":"","s_factor":275.0},{"company":"농협","product":"치료비안심해2NH건강보험","term":"10년이상","gubun":"","s_factor":525.0},{"company":"농협","product":"치료비안심해2NH건강보험","term":"15년이상","gubun":"","s_factor":725.0},{"company":"농협","product":"치료비안심해2NH건강보험","term":"20년이상","gubun":"","s_factor":900.0},{"company":"농협","product":"치료비안심해2NH건강보험","term":"갱신형","gubun":"","s_factor":1000.0},{"company":"동양","product":"우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)","term":"5년납","gubun":"보장형_평준납입형","s_factor":385.0},{"company":"동양","product":"우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)","term":"7년납","gubun":"","s_factor":454.99999999999994},{"company":"동양","product":"우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)","term":"10년납","gubun":"","s_factor":840.0},{"company":"동양","product":"우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)","term":"10년납","gubun":"보장형_체감납입형","s_factor":350.0},{"company":"동양","product":"우리WON하는 (간편)알뜰플러스종신  (해약환급금일부지급형)","term":"10년납","gubun":"표준형","s_factor":140.0},{"company":"동양","product":"우리WON하는유니버셜종신 (일반심사형,간편심사형)","term":"10년납","gubun":"건강체 표준체","s_factor":1085.0},{"company":"동양","product":"우리WON하는유니버셜종신 (일반심사형,간편심사형)","term":"15년납","gubun":"","s_factor":1435.0},{"company":"동양","product":"우리WON하는유니버셜종신 (일반심사형,간편심사형)","term":"20년납","gubun":"","s_factor":1715.0},{"company":"동양","product":"우리WON하는5배더행복한플러스종신","term":"15년납","gubun":"일반/간편","s_factor":499.5},{"company":"동양","product":"우리WON하는7배더행복한플러스종신","term":"20년납","gubun":"일반/간편","s_factor":536.5},{"company":"동양","product":"우리WON안심상속종신","term":"10년납","gubun":"일반/간편","s_factor":595.0},{"company":"동양","product":"우리WON안심상속종신","term":"15년납","gubun":"","s_factor":805.0},{"company":"동양","product":"우리WON안심상속종신","term":"20년납 이상","gubun":"","s_factor":1155.0},{"company":"동양","product":"우리WON하는건강플러스종신","term":"10년납","gubun":"해약환급금일부지급형","s_factor":525.0},{"company":"동양","product":"우리WON하는치매간병(주계약), 우리WON하는 건강한보장","term":"10년납이상","gubun":"해약환급금일부/미지급형 표준형","s_factor":420.0},{"company":"동양","product":"우리WON하는치매간병(주계약), 우리WON하는 건강한보장","term":"20년납이상","gubun":"","s_factor":1085.0},{"company":"동양","product":"우리WON하는 보장","term":"10년납","gubun":"일반","s_factor":420.0},{"company":"동양","product":"우리WON하는 보장","term":"20년납 이상","gubun":"","s_factor":1085.0},{"company":"동양","product":"우리WON하는 보장","term":"10년납 이상","gubun":"간편","s_factor":420.0},{"company":"동양","product":"우리WON하는 보장","term":"20년납이상","gubun":"","s_factor":1085.0},{"company":"동양","product":"우리WON하는보장(갱신형)","term":"20년납, 30년납","gubun":"일반/간편","s_factor":1085.0},{"company":"동양","product":"우리WON하는암 (해약환급금 일부지급형, 표준형)","term":"10년납","gubun":"일반/간편","s_factor":420.0},{"company":"동양","product":"우리WON하는암 (해약환급금 일부지급형, 표준형)","term":"20년납 이상","gubun":"","s_factor":1085.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"15년납","gubun":"종합설계형","s_factor":420.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"20년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"30년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"15년납","gubun":"종합설계형_ 출생후보장기간","s_factor":420.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"20년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"30년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"15년납","gubun":"3대질환보장형","s_factor":420.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"20년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"30년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"15년납","gubun":"3대질환보장형_ 출생후보장기간","s_factor":420.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"20년납","gubun":"","s_factor":735.0},{"company":"동양","product":"우리WON하는쑥쑥어린이보장 (해약환급금일부지급형Ⅲ)","term":"30년납","gubun":"","s_factor":735.0},{"company":"흥국","product":"미리받는트리플더블업건강종신","term":"20년납이상","gubun":"","s_factor":800.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"20년↑","gubun":"라이프 밸런스형","s_factor":800.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"15년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"10년↑(일반)","gubun":"","s_factor":440.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"10년↑(간편)","gubun":"","s_factor":400.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"20년↑","gubun":"프리미엄 보장형","s_factor":800.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"15년↑","gubun":"","s_factor":560.0},{"company":"흥국","product":"(간편한) 리턴100종신","term":"10년↑","gubun":"","s_factor":280.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"20년↑","gubun":"라이프 밸런스형","s_factor":800.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"15년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"10년↑","gubun":"","s_factor":480.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"20년↑","gubun":"프리미엄 보장형","s_factor":800.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"15년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"(간편한) 플렉스 리턴100종신","term":"10년↑","gubun":"","s_factor":320.0},{"company":"흥국","product":"치매담은시니어보장","term":"20년↑","gubun":"해약환급금 미지급형","s_factor":1100.0},{"company":"흥국","product":"치매담은시니어보장","term":"15년↑","gubun":"","s_factor":797.5000000000001},{"company":"흥국","product":"치매담은시니어보장","term":"10년↑","gubun":"","s_factor":522.5},{"company":"흥국","product":"치매담은시니어보장","term":"20년↑","gubun":"해약환급금 일부지급형","s_factor":935.0000000000001},{"company":"흥국","product":"치매담은시니어보장","term":"15년↑","gubun":"","s_factor":715.0000000000001},{"company":"흥국","product":"치매담은시니어보장","term":"10년↑","gubun":"","s_factor":440.00000000000006},{"company":"흥국","product":"치매담은시니어보장","term":"20년↑","gubun":"표준형","s_factor":797.5000000000001},{"company":"흥국","product":"치매담은시니어보장","term":"15년↑","gubun":"","s_factor":605.0},{"company":"흥국","product":"치매담은시니어보장","term":"10년↑","gubun":"","s_factor":385.00000000000006},{"company":"흥국","product":"치매담은Plus보장보험","term":"15년↑","gubun":"해약환급금 일부지급형","s_factor":715.0000000000001},{"company":"흥국","product":"치매담은Plus보장보험","term":"10년↑","gubun":"","s_factor":440.00000000000006},{"company":"흥국","product":"다(多)사랑통합","term":"20년↑","gubun":"해약환급금 미지급형","s_factor":1100.0},{"company":"흥국","product":"다(多)사랑통합","term":"15년↑","gubun":"","s_factor":715.0000000000001},{"company":"흥국","product":"다(多)사랑통합","term":"10년↑","gubun":"","s_factor":330.0},{"company":"흥국","product":"다(多)사랑통합","term":"20년↑","gubun":"표준형","s_factor":935.0000000000001},{"company":"흥국","product":"다(多)사랑통합","term":"15년↑","gubun":"","s_factor":715.0000000000001},{"company":"흥국","product":"다(多)사랑통합","term":"10년↑","gubun":"","s_factor":330.0},{"company":"흥국","product":"다(多)사랑통합","term":"20년↑","gubun":"갱신형","s_factor":1100.0},{"company":"흥국","product":"다(多)사랑통합","term":"10년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"오튼튼5.10.5건강보험, 다(多)사랑암","term":"20년↑","gubun":"해약환급금 미지급형","s_factor":1100.0},{"company":"흥국","product":"오튼튼5.10.5건강보험, 다(多)사랑암","term":"15년↑","gubun":"","s_factor":715.0000000000001},{"company":"흥국","product":"오튼튼5.10.5건강보험, 다(多)사랑암","term":"10년↑","gubun":"","s_factor":330.0},{"company":"흥국","product":"오튼튼5.10.5건강보험(갱신형)","term":"20년↑","gubun":"갱신형","s_factor":1100.0},{"company":"흥국","product":"다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험","term":"20년↑","gubun":"해약환급금 미지급형","s_factor":1100.0},{"company":"흥국","product":"다사랑3.10.5간편건강, 3.10.5.5고당플러스간편건강 3.N.5.N플러스간편건강보험","term":"10년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"3.1.1간편건강보험(갱신형)","term":"20년↑","gubun":"갱신형","s_factor":1100.0},{"company":"흥국","product":"다사랑3N5간편건강","term":"20년↑","gubun":"해약환급금 미지급형","s_factor":1100.0},{"company":"흥국","product":"다사랑3N5간편건강","term":"10년↑","gubun":"","s_factor":660.0},{"company":"흥국","product":"다사랑3N5간편건강","term":"20년↑","gubun":"표준형","s_factor":1100.0},{"company":"흥국","product":"다사랑3N5간편건강","term":"10년↑","gubun":"","s_factor":550.0},{"company":"라이나","product":"THE건강해지는 종신","term":"20년납","gubun":"해지환급금 미지급형","s_factor":1430.0000000000002},{"company":"라이나","product":"THE건강해지는 종신","term":"15년납","gubun":"","s_factor":1309.0},{"company":"라이나","product":"THE건강해지는 종신","term":"12년납","gubun":"","s_factor":1045.0},{"company":"라이나","product":"THE건강해지는 종신","term":"10년납","gubun":"","s_factor":742.5000000000001},{"company":"라이나","product":"THE건강해지는 종신","term":"20년납","gubun":"기본형","s_factor":357.50000000000006},{"company":"라이나","product":"THE건강해지는 종신","term":"15년납","gubun":"","s_factor":330.0},{"company":"라이나","product":"THE건강해지는 종신","term":"12년납","gubun":"","s_factor":302.5},{"company":"라이나","product":"THE건강해지는 종신","term":"10년납","gubun":"","s_factor":275.0},{"company":"라이나","product":"THE채우는 335 간편고지 종신, THE채우는 종신","term":"20년납","gubun":"해약환급금 일부지급형","s_factor":630.0},{"company":"라이나","product":"THE채우는 335 간편고지 종신, THE채우는 종신","term":"15년납","gubun":"","s_factor":570.0},{"company":"라이나","product":"THE채우는 335 간편고지 종신, THE채우는 종신","term":"10년납","gubun":"","s_factor":510.0},{"company":"라이나","product":"THE채우는 335 간편고지 종신, THE채우는 종신","term":"7년납","gubun":"","s_factor":390.0},{"company":"라이나","product":"THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신","term":"15년납이상","gubun":"해지환급금 미지급형","s_factor":1430.0000000000002},{"company":"라이나","product":"THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신","term":"10년납","gubun":"","s_factor":907.5000000000001},{"company":"라이나","product":"THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신","term":"15년납이상","gubun":"기본형","s_factor":275.0},{"company":"라이나","product":"THE(착한) 간편고지 종신, 전에없던 초간편종신, THE착한 간편고지 건강종신","term":"10년납","gubun":"","s_factor":192.50000000000003},{"company":"라이나","product":"전에없던실속치매 (해약환급금 미지급형)","term":"20년납이상","gubun":"주계약","s_factor":1102.5},{"company":"라이나","product":"전에없던실속치매 (해약환급금 미지급형)","term":"15년납","gubun":"","s_factor":990.0},{"company":"라이나","product":"전에없던실속치매 (해약환급금 미지급형)","term":"10년납","gubun":"","s_factor":720.0},{"company":"라이나","product":"암으로치료하였어도 OK암","term":"-","gubun":"","s_factor":900.0},{"company":"라이나","product":"THE실속있는치아, THE건강한치아V THE든든해진라이나치아","term":"10년만기","gubun":"갱신형","s_factor":1102.5},{"company":"라이나","product":"THE실속있는치아, THE건강한치아V THE든든해진라이나치아","term":"5년만기","gubun":"","s_factor":630.0},{"company":"라이나","product":"THE건강한치아보험V(리셋형)","term":"갱신형","gubun":"","s_factor":1102.5},{"company":"라이나","product":"골라담는(간편)건강보험 (갱신형)","term":"20년납","gubun":"주계약","s_factor":1102.5},{"company":"라이나","product":"골라담는(간편)건강보험 (갱신형)","term":"10년납","gubun":"","s_factor":684.0},{"company":"라이나","product":"새로담는 (간편)건강보험(클래식)","term":"해약환급금미지급형Ⅱ","gubun":"","s_factor":1102.5},{"company":"라이나","product":"새로담는 (간편)건강보험(클래식)","term":"기본형","gubun":"","s_factor":900.0},{"company":"라이나","product":"새로담는 간편건강보험(갱신형)","term":"20년납","gubun":"해약환급금 미지급형","s_factor":1102.5},{"company":"라이나","product":"새로담는 간편건강보험(갱신형)","term":"10년납","gubun":"","s_factor":684.0},{"company":"라이나","product":"브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)","term":"해약환급금미지급형Ⅱ","gubun":"","s_factor":1102.5},{"company":"라이나","product":"브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)","term":"","gubun":"","s_factor":1102.5},{"company":"라이나","product":"브레인케어건강(클래식), 새로운치아보험 덴탈어카운트, 새로담는건강플러스BLUE,GOLD(클래식)","term":"","gubun":"","s_factor":1102.5},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"10년미만","gubun":"저해약","s_factor":360.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"10-14년","gubun":"","s_factor":880.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"15-19년","gubun":"","s_factor":1160.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"20년납이상","gubun":"","s_factor":1280.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"10년미만","gubun":"일반형","s_factor":280.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"10-14년","gubun":"","s_factor":480.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"15-19년","gubun":"","s_factor":640.0},{"company":"교보","product":"교보(간편)평생건강보험 (기본보장형)","term":"20년납이상","gubun":"","s_factor":800.0},{"company":"교보","product":"교보(간편)K-실속종신보험","term":"5~6년","gubun":"-","s_factor":500.5},{"company":"교보","product":"교보(간편)K-실속종신보험","term":"7~9년","gubun":"-","s_factor":819.0},{"company":"교보","product":"교보(간편)K-실속종신보험","term":"10~14년","gubun":"-","s_factor":1183.0},{"company":"교보","product":"교보(간편)K-실속종신보험","term":"15년","gubun":"-","s_factor":1319.5},{"company":"교보","product":"교보(간편)모두지킴종신","term":"10년납 미만","gubun":"","s_factor":630.0},{"company":"교보","product":"교보(간편)모두지킴종신","term":"10년납-14년납","gubun":"","s_factor":909.9999999999999},{"company":"교보","product":"교보(간편)모두지킴종신","term":"15년납-19년납","gubun":"","s_factor":1014.9999999999999},{"company":"교보","product":"교보(간편)모두지킴종신","term":"20년납이상","gubun":"","s_factor":1120.0},{"company":"교보","product":"교보다시채움건강종신보험","term":"10년납 미만","gubun":"일반가입","s_factor":489.99999999999994},{"company":"교보","product":"교보다시채움건강종신보험","term":"10년납-14년납","gubun":"","s_factor":979.9999999999999},{"company":"교보","product":"교보다시채움건강종신보험","term":"15년납-19년납","gubun":"","s_factor":1085.0},{"company":"교보","product":"교보다시채움건강종신보험","term":"20년납 이상","gubun":"","s_factor":1260.0},{"company":"교보","product":"교보다시채움건강종신보험","term":"10년납 미만","gubun":"간편가입","s_factor":454.99999999999994},{"company":"교보","product":"교보다시채움건강종신보험","term":"10년납-14년납","gubun":"","s_factor":944.9999999999999},{"company":"교보","product":"교보다시채움건강종신보험","term":"15년납-19년납","gubun":"","s_factor":1050.0},{"company":"교보","product":"교보다시채움건강종신보험","term":"20년납 이상","gubun":"","s_factor":1225.0},{"company":"교보","product":"교보(간편)3밸런스보장보험PLUS","term":"5년납~6년납","gubun":"","s_factor":489.99999999999994},{"company":"교보","product":"교보(간편)3밸런스보장보험PLUS","term":"7년납~9년납","gubun":"","s_factor":630.0},{"company":"교보","product":"교보(간편)3밸런스보장보험PLUS","term":"10년납~14년납","gubun":"","s_factor":979.9999999999999},{"company":"교보","product":"교보(간편)3밸런스보장보험PLUS","term":"15년납~19년납","gubun":"","s_factor":1085.0},{"company":"교보","product":"교보(간편)3밸런스보장보험PLUS","term":"20년납 이상","gubun":"","s_factor":1155.0},{"company":"교보","product":"교보(간편)밸런스건강보험","term":"10년납-14년납","gubun":"","s_factor":700.0},{"company":"교보","product":"교보(간편)밸런스건강보험","term":"15년납-19년납","gubun":"","s_factor":979.9999999999999},{"company":"교보","product":"교보(간편)밸런스건강보험","term":"20년납이상","gubun":"","s_factor":1225.0},{"company":"교보","product":"실속건강종신보험 (기본형,보장강화형)","term":"10년미만","gubun":"-","s_factor":525.0},{"company":"교보","product":"실속건강종신보험 (기본형,보장강화형)","term":"10년","gubun":"-","s_factor":979.9999999999999},{"company":"교보","product":"실속건강종신보험 (기본형,보장강화형)","term":"12년","gubun":"","s_factor":979.9999999999999},{"company":"교보","product":"실속건강종신보험 (기본형,보장강화형)","term":"15-19년","gubun":"","s_factor":1155.0},{"company":"교보","product":"실속건강종신보험 (기본형,보장강화형)","term":"20년납이상","gubun":"-","s_factor":1400.0},{"company":"교보","product":"K-밸류업종신 (베이직,프라임형)","term":"-","gubun":"일반,간편","s_factor":1425.0},{"company":"교보","product":"K-밸류업종신 (라이트형)","term":"66세미만","gubun":"일반","s_factor":1425.0},{"company":"교보","product":"K-밸류업종신 (라이트형)","term":"66세이상","gubun":"","s_factor":1140.0},{"company":"교보","product":"K-밸류업종신 (라이트형)","term":"61세미만","gubun":"간편","s_factor":1425.0},{"company":"교보","product":"K-밸류업종신 (라이트형)","term":"61세이상","gubun":"","s_factor":1140.0},{"company":"교보","product":"교보경영인정기(보증비용부과형)","term":"20년납이상","gubun":"일반,간편","s_factor":1350.0},{"company":"교보","product":"교보(간편)치매·간병안심보험 (주계약기준)","term":"10년 미만","gubun":"","s_factor":425.0},{"company":"교보","product":"교보(간편)치매·간병안심보험 (주계약기준)","term":"10년-14년","gubun":"","s_factor":765.0},{"company":"교보","product":"교보(간편)치매·간병안심보험 (주계약기준)","term":"15년-19년","gubun":"","s_factor":1105.0},{"company":"교보","product":"교보(간편)치매·간병안심보험 (주계약기준)","term":"20년 이상","gubun":"","s_factor":1360.0},{"company":"KDB","product":"더블찬스종신Ⅱ","term":"5년납","gubun":"","s_factor":495.0},{"company":"KDB","product":"더블찬스종신Ⅱ","term":"7년납","gubun":"","s_factor":675.0},{"company":"KDB","product":"더블찬스종신Ⅱ","term":"10년납","gubun":"","s_factor":945.0},{"company":"KDB","product":"트리플찬스 종신","term":"10년납","gubun":"","s_factor":900.0},{"company":"KDB","product":"트리플찬스 종신","term":"15년납","gubun":"","s_factor":1080.0},{"company":"KDB","product":"트리플찬스 종신","term":"20년납","gubun":"","s_factor":1350.0},{"company":"KDB","product":"무심사 버팀목 종신 (해약환급금 일부(50%)지급형)","term":"5년납","gubun":"체증형","s_factor":450.0},{"company":"KDB","product":"무심사 버팀목 종신 (해약환급금 일부(50%)지급형)","term":"7년납","gubun":"","s_factor":630.0},{"company":"KDB","product":"무심사 버팀목 종신 (해약환급금 일부(50%)지급형)","term":"10년납","gubun":"","s_factor":900.0},{"company":"KDB","product":"서포트100건강종신","term":"10년납","gubun":"","s_factor":900.0},{"company":"KDB","product":"서포트100건강종신","term":"15년납","gubun":"","s_factor":1080.0},{"company":"KDB","product":"서포트100건강종신","term":"20년납이상","gubun":"","s_factor":1350.0},{"company":"KDB","product":"라이프핏건강보험, 버팀목 NEW케어보험","term":"5년납","gubun":"","s_factor":300.0},{"company":"KDB","product":"라이프핏건강보험, 버팀목 NEW케어보험","term":"7년납","gubun":"","s_factor":420.0},{"company":"KDB","product":"라이프핏건강보험, 버팀목 NEW케어보험","term":"10년납","gubun":"","s_factor":720.0},{"company":"KDB","product":"라이프핏건강보험, 버팀목 NEW케어보험","term":"15년납","gubun":"","s_factor":840.0},{"company":"KDB","product":"라이프핏건강보험, 버팀목 NEW케어보험","term":"20년납이상","gubun":"","s_factor":1020.0},{"company":"KDB","product":"암만생각해도 KDB암보험2.0","term":"10년납","gubun":"","s_factor":720.0},{"company":"KDB","product":"암만생각해도 KDB암보험2.0","term":"15년납","gubun":"","s_factor":840.0},{"company":"KDB","product":"암만생각해도 KDB암보험2.0","term":"20년납 이상","gubun":"","s_factor":1020.0},{"company":"KDB","product":"버팀목 치매보장","term":"10년납","gubun":"","s_factor":720.0},{"company":"KDB","product":"버팀목 치매보장","term":"15년납","gubun":"","s_factor":840.0},{"company":"KDB","product":"버팀목 치매보장","term":"20년납 이상","gubun":"","s_factor":1020.0},{"company":"KDB","product":"영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금","term":"5년납","gubun":"","s_factor":135.0},{"company":"KDB","product":"영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금","term":"7년납","gubun":"","s_factor":360.0},{"company":"KDB","product":"영리한 변액연금 더!행복드림변액연금 더!행복플러스UP연금","term":"10년납이상","gubun":"","s_factor":630.0},{"company":"KDB","product":"더!행복플러스종신","term":"10년납","gubun":"","s_factor":854.0},{"company":"KDB","product":"더!행복플러스종신","term":"20년납","gubun":"","s_factor":1098.0},{"company":"KDB","product":"더!행복세븐종신","term":"20년납","gubun":"","s_factor":1403.0},{"company":"ABL","product":"우리WON세븐종신보험","term":"20년납","gubun":"일반/간편","s_factor":1113.0},{"company":"ABL","product":"우리WON더채움종신보험 (해약환급금 일부지급형)","term":"10년납","gubun":"일반/간편","s_factor":756.0},{"company":"ABL","product":"우리WON더채움종신보험 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":840.0},{"company":"ABL","product":"우리WON더블종신 (해약환급금 일부지급형)","term":"7년납","gubun":"일반심사형 간편심사형","s_factor":672.0},{"company":"ABL","product":"우리WON더블종신 (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":986.9999999999999},{"company":"ABL","product":"우리WON더블종신 (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":1260.0},{"company":"ABL","product":"우리WON더블종신 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":1407.0},{"company":"ABL","product":"우리WON스테이블종신","term":"7년납","gubun":"일반심사형 간편심사형","s_factor":672.0},{"company":"ABL","product":"우리WON스테이블종신","term":"10년납","gubun":"","s_factor":756.0},{"company":"ABL","product":"우리WON스테이블종신","term":"15년납","gubun":"","s_factor":798.0},{"company":"ABL","product":"우리WON스테이블종신","term":"20년납","gubun":"","s_factor":840.0},{"company":"ABL","product":"우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)","term":"5년납","gubun":"일반심사형 간편심사형","s_factor":588.0},{"company":"ABL","product":"우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)","term":"7년납","gubun":"","s_factor":798.0},{"company":"ABL","product":"우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)","term":"10년납","gubun":"","s_factor":965.9999999999999},{"company":"ABL","product":"우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)","term":"15년납","gubun":"","s_factor":1260.0},{"company":"ABL","product":"우리WON상속종신보험, 우리WON상속종신보험Trust (해약환급금 미지급형)","term":"20년납","gubun":"","s_factor":1260.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"5년납","gubun":"평준형 (일반심사형) (간편심사형)","s_factor":630.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":609.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":1029.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":1365.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"20년이상","gubun":"","s_factor":1428.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"5년납","gubun":"체증형 (일반심사형) (간편심사형)","s_factor":588.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":609.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"10년납","gubun":"","s_factor":923.9999999999999},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":1239.0},{"company":"ABL","product":"우리WON드림종신III (해약환급금 일부지급형)","term":"20년이상","gubun":"","s_factor":1386.0},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"5년납","gubun":"해약환급금 미지급형","s_factor":378.0},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"10년납","gubun":"","s_factor":672.0},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"15년납","gubun":"","s_factor":965.9999999999999},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"20년납 이상","gubun":"","s_factor":1134.0},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"5년납","gubun":"기본형","s_factor":125.99999999999999},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"10년납","gubun":"","s_factor":482.99999999999994},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"15년납","gubun":"","s_factor":735.0},{"company":"ABL","product":"우리WON건강N더보장종합건강, 우리WON(3.10.5) 간편건강, 우리WON더담은암보험","term":"20년납 이상","gubun":"","s_factor":944.9999999999999},{"company":"ABL","product":"우리WON건강N더보장 종합건강보험","term":"10년 만기","gubun":"갱신형","s_factor":672.0},{"company":"ABL","product":"우리WON건강N더보장 종합건강보험","term":"20년&30년","gubun":"","s_factor":1134.0},{"company":"ABL","product":"우리WON케어간병 (해약환급금 미지급형) (주계약기준)","term":"10년납","gubun":"일반심사형 간편심사형","s_factor":399.0},{"company":"ABL","product":"우리WON케어간병 (해약환급금 미지급형) (주계약기준)","term":"15년납","gubun":"","s_factor":882.0},{"company":"ABL","product":"우리WON케어간병 (해약환급금 미지급형) (주계약기준)","term":"20년납이상","gubun":"","s_factor":1092.0},{"company":"ABL","product":"우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)","term":"5년납","gubun":"기본형","s_factor":125.99999999999999},{"company":"ABL","product":"우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)","term":"10년납","gubun":"","s_factor":482.99999999999994},{"company":"ABL","product":"우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)","term":"15년납","gubun":"","s_factor":735.0},{"company":"ABL","product":"우리WON톡톡튀는여성건강 (일반심사형, 간편심사형)","term":"20년이상","gubun":"","s_factor":944.9999999999999},{"company":"미래","product":"미래에셋생명 변액연금 (기본형)","term":"3년납이상","gubun":"보종코드: 21218","s_factor":16.0},{"company":"미래","product":"미래에셋생명 변액연금 (기본형)","term":"5년납이상","gubun":"","s_factor":200.0},{"company":"미래","product":"미래에셋생명 변액연금 (기본형)","term":"7년납이상","gubun":"","s_factor":312.0},{"company":"미래","product":"미래에셋생명 변액연금 (기본형)","term":"10년납이상","gubun":"","s_factor":440.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"5년납이상","gubun":"일반가입형, 간편고지형","s_factor":440.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"7년납이상","gubun":"","s_factor":560.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"10년납이상","gubun":"","s_factor":760.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"12년납이상","gubun":"","s_factor":840.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"15년납이상","gubun":"","s_factor":1160.0},{"company":"미래","product":"헤리티지 라이트 종신보험 (보증비용부과형)","term":"20년납이상","gubun":"","s_factor":1320.0},{"company":"미래","product":"헤리티지 변액정기보험 (실적배당형 계약)","term":"15년납이상","gubun":"일반가입형, 간편고지형","s_factor":1160.0},{"company":"미래","product":"헤리티지 변액정기보험 (실적배당형 계약)","term":"20년납이상","gubun":"","s_factor":1320.0},{"company":"미래","product":"헤리티지 변액정기보험 (실적배당형 계약)","term":"25년납이상","gubun":"","s_factor":1400.0},{"company":"미래","product":"암 걱정없는 암치료보험","term":"10년납이상","gubun":"갱신형","s_factor":550.0},{"company":"미래","product":"암 걱정없는 암치료보험","term":"20년납이상","gubun":"","s_factor":825.0000000000001},{"company":"미래","product":"M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)","term":"10년납이상","gubun":"일반가입형, 간편가입형","s_factor":550.0},{"company":"미래","product":"M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)","term":"15년납이상","gubun":"","s_factor":632.5},{"company":"미래","product":"M-케어 치매간병 (해약환급금이 없는 유형) (주계약기준)","term":"20년납이상","gubun":"","s_factor":715.0000000000001},{"company":"미래","product":"M-케어 건강보험 (특약유형W가입용) 일반/간편고지","term":"10년납이상","gubun":"기본형, 해약환급금이없는유형","s_factor":412.50000000000006},{"company":"미래","product":"M-케어 건강보험 (특약유형W가입용) 일반/간편고지","term":"15년납이상","gubun":"","s_factor":616.0},{"company":"미래","product":"M-케어 건강보험 (특약유형W가입용) 일반/간편고지","term":"20년납이상","gubun":"","s_factor":825.0000000000001},{"company":"미래","product":"M-케어 건강보험 (특약유형S가입용)","term":"10년납이상","gubun":"기본형, 해약환급금이없는유형","s_factor":412.50000000000006},{"company":"미래","product":"M-케어 건강보험 (특약유형S가입용)","term":"15년납이상","gubun":"","s_factor":616.0},{"company":"미래","product":"M-케어 건강보험 (특약유형S가입용)","term":"20년납이상","gubun":"","s_factor":825.0000000000001},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"10년납이상","gubun":"기본형","s_factor":165.0},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"15년납이상","gubun":"","s_factor":203.50000000000003},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"20년납이상","gubun":"","s_factor":247.50000000000003},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"25년납이상","gubun":"","s_factor":286.0},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"10년납이상","gubun":"해약환급금이없는유형","s_factor":412.50000000000006},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"15년납이상","gubun":"","s_factor":616.0},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지)_S가입용 (355간편고지 고당)_S가입용 (주계약)","term":"20년납이상","gubun":"","s_factor":825.0000000000001},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)","term":"10년납이상","gubun":"갱신형","s_factor":412.50000000000006},{"company":"미래","product":"M-케어 건강보험 (3.10.5간편고지),(355간편고지 고당)","term":"20년납이상","gubun":"","s_factor":825.0000000000001},{"company":"하나","product":"하나로 THE연결된 종신","term":"5년납","gubun":"일반심사형 간편심사형","s_factor":363.00000000000006},{"company":"하나","product":"하나로 THE연결된 종신","term":"7년납","gubun":"","s_factor":473.00000000000006},{"company":"하나","product":"하나로 THE연결된 종신","term":"10년납","gubun":"","s_factor":550.0},{"company":"하나","product":"하나로 THE연결된 종신","term":"15년/20년납","gubun":"","s_factor":990.0000000000001},{"company":"하나","product":"하나원!투!종신","term":"5년납","gubun":"일반심사형 간편심사형","s_factor":308.0},{"company":"하나","product":"하나원!투!종신","term":"7년납","gubun":"","s_factor":330.0},{"company":"하나","product":"하나원!투!종신","term":"10년납","gubun":"","s_factor":418.00000000000006},{"company":"하나","product":"CEO경영인정기보험 (전기납)","term":"해약환급금 일부지급형","gubun":"","s_factor":1440.0},{"company":"하나","product":"CEO경영인정기보험 (전기납)","term":"일반형","gubun":"","s_factor":800.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"10년납","gubun":"해약환급금 미지급형","s_factor":640.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"15년납","gubun":"","s_factor":720.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"20년납","gubun":"","s_factor":880.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"10년납","gubun":"해약환급금 일부지급형","s_factor":480.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"15년납","gubun":"","s_factor":640.0},{"company":"하나","product":"하나더넥스트케어 (주계약기준)","term":"20년납","gubun":"","s_factor":760.0},{"company":"하나","product":"하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험","term":"10년납","gubun":"해약환급금 미지급형/갱신형","s_factor":520.0},{"company":"하나","product":"하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험","term":"20년/30년납","gubun":"","s_factor":880.0},{"company":"하나","product":"하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험","term":"10년납","gubun":"일반형","s_factor":360.0},{"company":"하나","product":"하나로 누리는 건강보험, 하나로라이트3.10.5간편건강보험","term":"20년/30년납","gubun":"","s_factor":680.0},{"company":"하나","product":"THE든든한연금","term":"전기납","gubun":"일반/간편","s_factor":605.0},{"company":"하나","product":"하나뿐인 변액연금","term":"5년납","gubun":"적립형","s_factor":220.00000000000003},{"company":"하나","product":"하나뿐인 변액연금","term":"7년납","gubun":"","s_factor":440.00000000000006},{"company":"하나","product":"하나뿐인 변액연금","term":"10년납 이상","gubun":"","s_factor":715.0000000000001},{"company":"푸본현대","product":"MAX 종신보험 원픽 (해약환급금 일부지급형)","term":"5년납","gubun":"일반가입 간편가입","s_factor":330.0},{"company":"푸본현대","product":"MAX 종신보험 원픽 (해약환급금 일부지급형)","term":"7년납","gubun":"","s_factor":880.0},{"company":"푸본현대","product":"MAX 종신보험 원픽 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":1600.0},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"10년납","gubun":"10년","s_factor":330.0},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"10년납","gubun":"11~20년","s_factor":550.0},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"20년납","gubun":"","s_factor":770.0000000000001},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"10년납","gubun":"21~30년","s_factor":550.0},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"20년납이상","gubun":"","s_factor":990.0000000000001},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"10년납","gubun":"31년이상","s_factor":440.00000000000006},{"company":"푸본현대","product":"정기보험 스마트픽 (해약환급금미지급형/표준형)","term":"20년납이상","gubun":"","s_factor":880.0000000000001},{"company":"푸본현대","product":"MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)","term":"55세미만","gubun":"일반가입","s_factor":1419.0000000000002},{"company":"푸본현대","product":"MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)","term":"55세이상","gubun":"","s_factor":1320.0},{"company":"푸본현대","product":"MAX 경영인정기 탑픽Ⅱ (해약환급금 일부지급형)","term":"-","gubun":"간편가입","s_factor":1419.0000000000002},{"company":"푸본현대","product":"건강보험 마이픽 (해약환급금 일부지급형)","term":"10년납","gubun":"주계약","s_factor":250.0},{"company":"푸본현대","product":"건강보험 마이픽 (해약환급금 일부지급형)","term":"15년납","gubun":"","s_factor":330.0},{"company":"푸본현대","product":"건강보험 마이픽 (해약환급금 일부지급형)","term":"20년납","gubun":"","s_factor":425.0},{"company":"푸본현대","product":"건강보험 마이픽 (해약환급금 일부지급형)","term":"30년납","gubun":"","s_factor":425.0},{"company":"푸본현대","product":"MAX 연금다운\xa0연금보험","term":"10년납","gubun":"1형 보증비용부과형","s_factor":546.0},{"company":"푸본현대","product":"MAX 연금다운\xa0연금보험","term":"20년납","gubun":"","s_factor":611.0},{"company":"푸본현대","product":"MAX 연금다운\xa0연금보험","term":"10년납","gubun":"2형 보증비용미부과형","s_factor":130.0},{"company":"푸본현대","product":"MAX 연금다운\xa0연금보험","term":"20년납","gubun":"","s_factor":162.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"5년","gubun":"1형 연금액강화형","s_factor":162.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"7년","gubun":"","s_factor":227.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"10년","gubun":"","s_factor":357.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"5년","gubun":"2형 일반연금형","s_factor":32.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"7년","gubun":"","s_factor":97.5},{"company":"푸본현대","product":"MAX UP\xa0연금보험","term":"10년","gubun":"","s_factor":130.0},{"company":"IM","product":"당당한 인생종신 (체증형)","term":"5년납","gubun":"일반","s_factor":556.8000000000001},{"company":"IM","product":"당당한 인생종신 (체증형)","term":"7년납","gubun":"","s_factor":873.2},{"company":"IM","product":"당당한 인생종신 (체증형)","term":"5년납","gubun":"간편","s_factor":544.0},{"company":"IM","product":"당당한 인생종신 (체증형)","term":"7년납","gubun":"","s_factor":858.4},{"company":"IM","product":"더(THE) 행복한 종신보험","term":"20년이상","gubun":"","s_factor":666.0},{"company":"IM","product":"iM Plus세븐UP종신보험","term":"20년","gubun":"일반,간편","s_factor":932.4},{"company":"IM","product":"iM Plus세븐UP골드종신보험","term":"20년","gubun":"일반,간편","s_factor":1346.8},{"company":"IM","product":"iM 트래블PRO변액연금","term":"5년납","gubun":"","s_factor":229.4},{"company":"IM","product":"iM 트래블PRO변액연금","term":"7년납","gubun":"","s_factor":414.4},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"10년/12년","gubun":"보험료 10만원이상","s_factor":140.6},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"15년/20년이상","gubun":"","s_factor":236.8},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"10이상","gubun":"보험료 20만원이상","s_factor":577.2},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"12년이상","gubun":"","s_factor":606.8},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"15년/20년이상","gubun":"","s_factor":651.2},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"5년이상","gubun":"보험료 30만원이상","s_factor":214.6},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"7년이상","gubun":"","s_factor":370.0},{"company":"IM","product":"(오토파일럿) 마이솔루션AI변액연금보험S","term":"5년이상","gubun":"50만원 이상","s_factor":244.2},{"company":"IM","product":"든든한 인생치매 (주계약기준)","term":"5년납","gubun":"","s_factor":569.8},{"company":"IM","product":"든든한 인생치매 (주계약기준)","term":"7년납","gubun":"","s_factor":799.2},{"company":"IM","product":"iM Active Care 치매간병보험 (해약환급금 미지급형)","term":"10년","gubun":"1종,2종","s_factor":414.4},{"company":"IM","product":"iM Active Care 치매간병보험 (해약환급금 미지급형)","term":"15년","gubun":"","s_factor":614.2},{"company":"IM","product":"iM Active Care 치매간병보험 (해약환급금 미지급형)","term":"20년이상","gubun":"","s_factor":806.6},{"company":"IM","product":"iM Plus세븐UP 더좋은종신보험","term":"20년납","gubun":"","s_factor":932.4},{"company":"IBK","product":"(무)IBK NEW 프리미엄 연금보험","term":"5년납","gubun":"","s_factor":250.0},{"company":"IBK","product":"(무)IBK NEW 프리미엄 연금보험","term":"7년납","gubun":"","s_factor":400.0},{"company":"IBK","product":"(무)IBK NEW 프리미엄 연금보험","term":"10년납이상","gubun":"","s_factor":500.0},{"company":"IBK","product":"(무)IBK 프리미엄 연금보험","term":"5년납","gubun":"","s_factor":220.0},{"company":"IBK","product":"(무)IBK 프리미엄 연금보험","term":"7년납","gubun":"","s_factor":380.0},{"company":"IBK","product":"(무)IBK 프리미엄 연금보험","term":"10년납이상","gubun":"","s_factor":450.0},{"company":"IBK","product":"연금액 평생보증받는 변액연금, 평생든든변액연금","term":"5년납","gubun":"","s_factor":170.0},{"company":"IBK","product":"연금액 평생보증받는 변액연금, 평생든든변액연금","term":"7년납","gubun":"","s_factor":400.0},{"company":"IBK","product":"연금액 평생보증받는 변액연금, 평생든든변액연금","term":"10,11년납","gubun":"","s_factor":600.0},{"company":"IBK","product":"연금액 평생보증받는 변액연금, 평생든든변액연금","term":"12년납이상","gubun":"","s_factor":600.0},{"company":"IBK","product":"(무)IBK하이브리드 연금저축","term":"5년납","gubun":"","s_factor":150.0},{"company":"IBK","product":"(무)IBK하이브리드 연금저축","term":"7년납","gubun":"","s_factor":250.0},{"company":"IBK","product":"(무)IBK하이브리드 연금저축","term":"10년납이상","gubun":"","s_factor":350.0}]'
EMBEDDED_RATES_DATA = {
  "life_rules": {
    "next_month_rate": 3.32,
    "company_installments": {
      "흥국": {
        "default": 0.96,
        "건강": 0.96,
        "종신": 0.96,
        "오튼튼": 0.96,
        "다사랑": 0.96
      },
      "한화": {
        "default": 1.56,
        "H종신": 1.56,
        "제로백": 1.56,
        "일반보장": 2.76
      },
      "DB": {
        "default": 1.32,
        "건강": 1.32,
        "알행종": 1.56
      },
      "신한": {
        "default": 0.84,
        "건강": 0.84,
        "종신": 1.56
      },
      "KB": {
        "default": 3.48
      },
      "메트": {
        "default": 3.84,
        "연금": 4.8,
        "종신": 3.84,
        "백만인": 2.52
      },
      "농협": {
        "default": 1.56,
        "투스텝": 1.56,
        "기타": 0.6
      },
      "동양": {
        "default": 1.08,
        "어린이": 1.08,
        "쑥쑥": 1.08,
        "단기납": 1.56,
        "종신": 1.8,
        "경영인": 2.28
      },
      "라이나": {
        "default": 1.56,
        "건강": 1.56
      },
      "교보": {
        "default": 2.76
      },
      "KDB": {
        "default": 1.56
      },
      "ABL": {
        "default": 1.56
      },
      "미래": {
        "default": 2.76
      },
      "하나": {
        "default": 0.96,
        "건강": 0.96,
        "일반": 1.56
      },
      "푸본현대": {
        "default": 1.56,
        "표준": 6.12,
        "MAX원픽": 1.56,
        "마이픽": 1.56
      },
      "IM": {
        "default": 2.04
      },
      "IBK": {
        "default": 2.76
      }
    },
    "incentives": {
      "흥국": {
        "전략": {
          "name": "흥국생명 전략 6종 (오튼튼/다사랑 등)",
          "next_month_base": 4.0,
          "next_month_sky": 2.0,
          "install_period_bonus": 6.0,
          "install_strategy_bonus": 2.0,
          "total_rate": 14.0,
          "note": "20만원 구간 기준, 본사 전략시책(+200%) 포함"
        },
        "일반": {
          "name": "흥국생명 일반 건강",
          "next_month_base": 4.0,
          "next_month_sky": 0.0,
          "install_period_bonus": 6.0,
          "install_strategy_bonus": 0.0,
          "total_rate": 10.0,
          "note": "20만원 구간 기준"
        }
      }
    }
  },
  "nonlife_rules": {
    "conversion_rate": 0.92,
    "next_month_rate": 6.1,
    "installment_rate": 1.32,
    "total_commission_rate": 7.42,
    "companies": [
      "현대해상",
      "메리츠",
      "KB손보",
      "한화손보",
      "DB손보",
      "롯데손보",
      "흥국화재",
      "농협손보",
      "하나손보"
    ],
    "incentives": {
      "현대해상": {
        "주력": {
          "name": "현대해상 주력보종 (퍼펙트/간편/굿앤굿)",
          "next_month_base": 1.0,
          "next_month_sky": 2.6,
          "install_week_bonus": 2.0,
          "install_main_bonus": 3.0,
          "install_sky_2nd": 1.7,
          "total_rate": 10.3,
          "note": "1주차 가동(200%) + 주력가동(300%) + SKY 2차년도(170%) 포함"
        },
        "일반": {
          "name": "현대해상 일반 인보험",
          "next_month_base": 1.0,
          "next_month_sky": 2.6,
          "install_week_bonus": 2.0,
          "install_main_bonus": 0.0,
          "install_sky_2nd": 1.7,
          "total_rate": 7.3,
          "note": "주력보종 가동시상(300%) 제외"
        }
      },
      "KB손보": {
        "주력": {
          "name": "KB손해보험 1주차 주력보종",
          "next_month_base": 1.0,
          "next_month_sky": 2.6,
          "install_week_bonus": 2.0,
          "install_main_bonus": 2.0,
          "install_sky_2nd": 0.0,
          "total_rate": 7.6,
          "note": "익월 360% + 1주차 가동 200% + 주력 200%"
        }
      },
      "한화손보": {
        "주력": {
          "name": "한화손해보험 1주차 주력보종",
          "next_month_base": 1.0,
          "next_month_sky": 0.5,
          "install_week_bonus": 4.0,
          "install_main_bonus": 2.0,
          "install_sky_2nd": 0.0,
          "total_rate": 7.5,
          "note": "익월 150% + 1주차 인보험 400% + 주력 200%"
        }
      },
      "메리츠": {
        "주력": {
          "name": "메리츠화재 1주차 주력보종",
          "next_month_base": 1.0,
          "next_month_sky": 2.5,
          "install_week_bonus": 2.0,
          "install_main_bonus": 2.0,
          "install_sky_2nd": 0.0,
          "total_rate": 7.5,
          "note": "익월 350% + 1주차 가동 200% + 주력 200%"
        }
      }
    }
  }
}

import json
import re
import os
from typing import Dict, Any, Optional, List, Tuple




LIFE_PRODUCTS = json.loads(EMBEDDED_LIFE_DATA)
COMPANY_RATES = EMBEDDED_RATES_DATA

LIFE_RULES = COMPANY_RATES['life_rules']
NONLIFE_RULES = COMPANY_RATES['nonlife_rules']


def parse_premium(text: str) -> Optional[int]:
    """텍스트에서 보험료(원 단위)를 추출"""
    # 20만원, 20만, 200,000, 200000, 100만, 10만원 등
    m = re.search(r'(\d+[\d,]*)\s*만\s*원?', text)
    if m:
        num = int(m.group(1).replace(',', ''))
        return num * 10000
    m2 = re.search(r'(\d+[\d,]{3,})\s*원?', text)
    if m2:
        return int(m2.group(1).replace(',', ''))
    # 숫자만 있고 뒤에 '만' 없이 10~500 사이면 만원 단위로 추정
    m3 = re.search(r'\b(\d{1,4})\b', text)
    if m3:
        val = int(m3.group(1))
        if val in [5, 10, 15, 20, 25, 30, 40, 50, 100, 200, 300, 500]:
            return val * 10000
    return None


def search_life_product(company: str, query: str, term: str = "") -> Optional[Dict[str, Any]]:
    """생보사 조견표에서 가장 근접한 상품 검색"""
    comp_cleaned = company.replace('생명', '').strip()
    candidates = [p for p in LIFE_PRODUCTS if p['company'] == comp_cleaned or comp_cleaned in p['company']]
    
    if not candidates:
        return None
    
    # 1. 쿼리 키워드 매칭
    keywords = [k for k in re.split(r'\s+', query) if k and k not in [comp_cleaned, '생명', '생보']]
    
    scored_candidates = []
    for p in candidates:
        score = 0
        p_name = p['product']
        p_term = p.get('term', '')
        p_gubun = p.get('gubun', '')
        full_text = f"{p_name} {p_term} {p_gubun}"
        
        for kw in keywords:
            if kw in p_name:
                score += 5
            elif kw in full_text:
                score += 2
        
        if term:
            if term in p_term:
                score += 10
            elif term.replace('년납', '').replace('년', '') in p_term:
                score += 8
                
        if score > 0:
            scored_candidates.append((score, p))
            
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    if scored_candidates:
        return scored_candidates[0][1]
    
    # 키워드 매칭이 없으면 첫 후보 반환하지 않고 None
    return None


def calculate_life(
    company: str,
    product_name: str,
    premium: int,
    s_factor: float,
    term: str = "",
    incentive_type: str = "전략"
) -> Dict[str, Any]:
    """생명보험 수수료 및 시책 계산"""
    comp_clean = company.replace('생명', '').strip()
    
    # 1. S환산 성적
    # 1,000천원(=100만원) 기준이므로 premium * (s_factor / 1,000)
    s_grade = round(premium * (s_factor / 1000.0))
    conversion_rate = (s_factor / 1000.0) * 100
    
    # 2. 수수료 계산
    next_month_rate = LIFE_RULES['next_month_rate']  # 3.32 (332%)
    next_month_comm = round(s_grade * next_month_rate)
    
    # 회사별 분급 지급율
    comp_inst_dict = LIFE_RULES['company_installments'].get(comp_clean, {"default": 1.56})
    inst_rate = comp_inst_dict.get('default', 1.56)
    for k, v in comp_inst_dict.items():
        if k != 'default' and (k in product_name or k in term):
            inst_rate = v
            break
            
    installment_comm = round(s_grade * inst_rate)
    total_comm = next_month_comm + installment_comm
    
    # 3. 시책 계산
    inc_dict = LIFE_RULES['incentives'].get(comp_clean, {})
    inc_rule = inc_dict.get(incentive_type) or inc_dict.get('전략') or inc_dict.get('일반')
    
    if inc_rule:
        next_month_inc_rate = inc_rule.get('next_month_base', 0.0) + inc_rule.get('next_month_sky', 0.0)
        split_inc_rate = inc_rule.get('install_period_bonus', 0.0) + inc_rule.get('install_strategy_bonus', 0.0)
        next_month_inc = round(premium * next_month_inc_rate)
        split_inc = round(premium * split_inc_rate)
        total_inc = next_month_inc + split_inc
        inc_note = inc_rule.get('note', '')
        total_inc_rate = inc_rule.get('total_rate', next_month_inc_rate + split_inc_rate) * 100
    else:
        # 등록된 시책 규칙이 없으면 기본 0 처리 또는 메모
        next_month_inc_rate = 0.0
        split_inc_rate = 0.0
        next_month_inc = 0
        split_inc = 0
        total_inc = 0
        inc_note = "전단지별 시책 추가 확인 필요"
        total_inc_rate = 0.0
        
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    return {
        "category": "생명보험",
        "company": comp_clean + "생명",
        "product_name": product_name,
        "term": term,
        "premium": premium,
        "s_factor": s_factor,
        "conversion_rate": round(conversion_rate, 1),
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
        "total_inc_rate": round(total_inc_rate, 1),
        "inc_note": inc_note,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total
    }


def calculate_nonlife(
    company: str,
    product_name: str,
    premium: int,
    incentive_type: str = "주력"
) -> Dict[str, Any]:
    """손해보험 수수료 및 시책 계산"""
    comp_clean = company.replace('손해보험', '').replace('손보', '').replace('화재', '').strip()
    
    # 1. S환산 성적: 보험료의 92% 고정
    conv_rate = NONLIFE_RULES['conversion_rate']  # 0.92
    s_grade = round(premium * conv_rate)
    
    # 2. 수수료 계산
    next_month_rate = NONLIFE_RULES['next_month_rate']  # 6.10 (610%)
    inst_rate = NONLIFE_RULES['installment_rate']  # 1.32 (132%)
    next_month_comm = round(s_grade * next_month_rate)
    installment_comm = round(s_grade * inst_rate)
    total_comm = round(s_grade * NONLIFE_RULES['total_commission_rate'])
    
    # 3. 시책 계산
    inc_companies = NONLIFE_RULES['incentives']
    matched_comp = None
    for k in inc_companies.keys():
        if comp_clean in k or k in comp_clean:
            matched_comp = k
            break
            
    if matched_comp:
        comp_inc_dict = inc_companies[matched_comp]
        inc_rule = comp_inc_dict.get(incentive_type) or comp_inc_dict.get('주력') or list(comp_inc_dict.values())[0]
        next_month_inc_rate = inc_rule.get('next_month_base', 0.0) + inc_rule.get('next_month_sky', 0.0)
        split_inc_rate = inc_rule.get('install_week_bonus', 0.0) + inc_rule.get('install_main_bonus', 0.0) + inc_rule.get('install_sky_2nd', 0.0)
        next_month_inc = round(premium * next_month_inc_rate)
        split_inc = round(premium * split_inc_rate)
        total_inc = next_month_inc + split_inc
        inc_note = inc_rule.get('note', '')
        total_inc_rate = inc_rule.get('total_rate', next_month_inc_rate + split_inc_rate) * 100
    else:
        next_month_inc_rate = 0.0
        split_inc_rate = 0.0
        next_month_inc = 0
        split_inc = 0
        total_inc = 0
        inc_note = "원수사 1주차 전단지 참조"
        total_inc_rate = 0.0
        
    total_next_month = next_month_comm + next_month_inc
    total_split = installment_comm + split_inc
    grand_total = total_comm + total_inc
    
    return {
        "category": "손해보험",
        "company": comp_clean + "손보" if not comp_clean.endswith(('화재', '해상')) else comp_clean,
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
        "total_inc_rate": round(total_inc_rate, 1),
        "inc_note": inc_note,
        "total_next_month": total_next_month,
        "total_split": total_split,
        "grand_total": grand_total
    }


def parse_and_calculate(user_utterance: str) -> Dict[str, Any]:
    """사용자의 자연어 메시지나 파라미터를 분석해 적절한 계산 수행"""
    text = user_utterance.strip()
    
    # 1. 보험료 추출
    premium = parse_premium(text)
    if not premium:
        premium = 200000  # 기본값 20만원
        
    # 2. 납기 추출 (10년납, 20년납, 15년납 등)
    m_term = re.search(r'(\d+)\s*년\s*납?', text)
    term = f"{m_term.group(1)}년납" if m_term else ""
    
    # 3. 생보사 목록 대조
    life_companies = ['흥국', '한화', 'DB', '신한', 'KB', '메트', '농협', '동양', '라이나', '교보', 'KDB', 'ABL', '미래', '하나', '푸본', 'IM', 'IBK']
    nonlife_companies = ['현대', '메리츠', 'KB손', '한화손', 'DB손', '롯데', '흥국화재', '농협손', '하나손', '손보']
    
    # 생보/손보 판별
    is_nonlife = any(c in text for c in nonlife_companies) or '손보' in text or '손해보험' in text
    
    if is_nonlife:
        comp_name = "현대해상"
        for c in ['현대해상', '현대', '메리츠', 'KB손보', 'KB손', '한화손보', '한화손', 'DB손보', 'DB손', '롯데손보', '롯데', '흥국화재', '농협손보', '농협손']:
            if c in text:
                comp_name = c
                break
        prod_name = "주력보종"
        for p in ['퍼펙트', '간편', '굿앤굿', '주력', '종합', '자녀']:
            if p in text:
                prod_name = p
                break
        return calculate_nonlife(comp_name, prod_name, premium, incentive_type="주력")
    
    # 생명보험 판정
    comp_name = "흥국"
    for c in life_companies:
        if c in text:
            comp_name = c
            break
            
    # 상품 검색
    matched = search_life_product(comp_name, text, term=term)
    if matched:
        return calculate_life(
            company=matched['company'],
            product_name=matched['product'],
            premium=premium,
            s_factor=matched['s_factor'],
            term=matched.get('term', term),
            incentive_type="전략" if "전략" in text or "오튼튼" in text or "다사랑" in text else "일반"
        )
    else:
        # 매칭되는 세부 상품이 없을 때 대표 기본값
        if comp_name == "흥국":
            s_factor = 1100.0  # 오튼튼 20년납
            prod_name = "다사랑·오튼튼(종합)"
        elif comp_name == "한화":
            s_factor = 1140.0  # 제로백 10년납
            prod_name = "제로백H종신"
        elif comp_name == "동양":
            s_factor = 735.0  # 쑥쑥어린이 20년납
            prod_name = "우리WON하는쑥쑥어린이"
        else:
            s_factor = 1000.0
            prod_name = f"{comp_name}생명 일반보장"
            
        return calculate_life(
            company=comp_name,
            product_name=prod_name,
            premium=premium,
            s_factor=s_factor,
            term=term or "20년납",
            incentive_type="전략"
        )


from typing import Dict, Any, List


def format_money(val: int) -> str:
    return f"{val:,}원"


def build_kakao_response(calc_result: Dict[str, Any]) -> Dict[str, Any]:
    """카카오 i 오픈빌더 규격(ItemCard)으로 응답 JSON 생성"""
    cat = calc_result['category']
    comp = calc_result['company']
    prod = calc_result['product_name']
    term = calc_result.get('term', '')
    premium = calc_result['premium']
    
    sub_title = f"{comp} · {prod}"
    sub_desc = f"{term} | 월납 {format_money(premium)}" if term else f"월납 {format_money(premium)}"
    
    item_list = [
        {"title": "S환산 성적", "description": f"{format_money(calc_result['s_grade'])} ({calc_result['conversion_rate']}%)"},
        {"title": f"익월 수수료 ({calc_result['next_month_comm_rate']}%)", "description": format_money(calc_result['next_month_comm'])},
        {"title": f"분급 수수료 ({calc_result['installment_comm_rate']}%)", "description": format_money(calc_result['installment_comm'])},
        {"title": "수수료 소계", "description": format_money(calc_result['total_comm'])},
        {"title": f"익월 시상 ({calc_result['next_month_inc_rate']}%)", "description": format_money(calc_result['next_month_inc'])},
        {"title": f"13회차/분할시상 ({calc_result['split_inc_rate']}%)", "description": format_money(calc_result['split_inc'])},
        {"title": f"시상 소계 ({calc_result['total_inc_rate']}%)", "description": format_money(calc_result['total_inc'])},
        {"title": "👉 익월 총수령", "description": format_money(calc_result['total_next_month'])},
        {"title": "👉 분급·차년도 총수령", "description": format_money(calc_result['total_split'])}
    ]
    
    quick_replies = [
        {"messageText": "흥국 오튼튼 20만 20년납", "action": "message", "label": "흥국 오튼튼 20만"},
        {"messageText": "현대해상 주력 20만", "action": "message", "label": "현대 주력 20만"},
        {"messageText": "한화 제로백 100만 10년납", "action": "message", "label": "한화 제로백 100만"},
        {"messageText": "동양 쑥쑥 20만 15년납", "action": "message", "label": "동양 쑥쑥 20만"},
        {"messageText": "도움말", "action": "message", "label": "💡 사용법 안내"}
    ]
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "itemCard": {
                        "imageTitle": {
                            "title": "스카이블루에셋 안양비전본부",
                            "description": "2026년 11월 수수료·시책 정산 시뮬레이션"
                        },
                        "title": sub_title,
                        "description": sub_desc,
                        "itemList": item_list,
                        "itemListAlignment": "right",
                        "itemListSummary": {
                            "title": "💰 최종 총수령액",
                            "description": format_money(calc_result['grand_total'])
                        }
                    }
                }
            ],
            "quickReplies": quick_replies
        }
    }


def build_help_response() -> Dict[str, Any]:
    """도움말 및 사용법 안내 응답"""
    help_text = (
        "💡 [안양비전본부 정산 챗봇 사용법]\n\n"
        "채팅창에 회사명, 상품명, 보험료를 자유롭게 입력하시면 즉시 수수료와 시책을 계산해 드립니다.\n\n"
        "📌 [입력 예시]\n"
        "1. 생명보험:\n"
        "  - '흥국 오튼튼 20만 20년납'\n"
        "  - '한화 제로백 100만 10년납'\n"
        "  - '동양 쑥쑥 20만 15년납'\n\n"
        "2. 손해보험:\n"
        "  - '현대해상 주력 20만'\n"
        "  - 'KB손보 20만'\n"
        "  - '손보 20만원'\n\n"
        "※ 생보사는 상품별 조견표 S환산(100만원 기준)과 회사별 분급 규정, 11월 시책이 자동 적용됩니다.\n"
        "※ 손보사는 보험료의 92% 환산, 익월 610%, 분급 132% 및 1주차 시책이 적용됩니다."
    )
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": help_text
                    }
                }
            ],
            "quickReplies": [
                {"messageText": "흥국 오튼튼 20만 20년납", "action": "message", "label": "흥국 오튼튼 20만"},
                {"messageText": "현대해상 주력 20만", "action": "message", "label": "현대해상 주력 20만"},
                {"messageText": "한화 제로백 100만 10년납", "action": "message", "label": "한화 제로백 100만"}
            ]
        }
    }


app = FastAPI(
    title="SkyBlue Asset Anyang Vision - Kakao Commission Chatbot",
    description="스카이블루에셋 안양비전본부 전용 수수료 및 시책 계산 챗봇 스킬 서버",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DirectCalcRequest(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    company: Optional[str] = None
    product_name: Optional[str] = None
    premium: Optional[int] = 200000
    s_factor: Optional[float] = None
    term: Optional[str] = "20년납"
    incentive_type: Optional[str] = "전략"

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "스카이블루에셋 안양비전본부 정산 챗봇 스킬 서버",
        "version": "1.0.0",
        "endpoints": {
            "kakao_skill": "/skill/calculate",
            "rest_api": "/api/calculate"
        }
    }

@app.post("/skill/calculate")
async def kakao_skill_calculate(request: Request):
    try:
        body = await request.json()
    except Exception:
        return build_help_response()

    user_request = body.get("userRequest", {})
    utterance = user_request.get("utterance", "").strip()

    if not utterance or utterance in ["도움말", "사용법", "메뉴", "시작", "help", "?"]:
        return build_help_response()

    try:
        calc_result = parse_and_calculate(utterance)
        return build_kakao_response(calc_result)
    except Exception as e:
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"⚠️ 계산 중 오류가 발생했습니다: {str(e)}\n\n'흥국 오튼튼 20만' 또는 '현대해상 주력 20만' 형식으로 다시 입력해 주세요."
                        }
                    }
                ]
            }
        }

@app.post("/api/calculate")
def api_calculate(req: DirectCalcRequest):
    if req.query:
        return parse_and_calculate(req.query)

    if req.category == "손해보험" or (req.company and any(c in req.company for c in ["현대", "손보", "화재", "메리츠", "KB손", "한화손", "DB손"])):
        return calculate_nonlife(
            company=req.company or "현대해상",
            product_name=req.product_name or "주력보종",
            premium=req.premium or 200000,
            incentive_type=req.incentive_type or "주력"
        )
    else:
        return calculate_life(
            company=req.company or "흥국",
            product_name=req.product_name or "다사랑·오튼튼",
            premium=req.premium or 200000,
            s_factor=req.s_factor or 1100.0,
            term=req.term or "20년납",
            incentive_type=req.incentive_type or "전략"
        )
