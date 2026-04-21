"""
自动打卡工具 — BeeWare Android App
"""

import requests
import json
import random
from datetime import datetime

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


LOCATIONS = {
    "兴化": {
        "longitude_range": (119.849000, 119.850000),
        "latitude_range": (32.940500, 32.941500),
        "address": "兴化市生态环境局"
    },
    "南大": {
        "longitude": "118.776441",
        "latitude": "32.058625",
        "address": "南京大学科学楼"
    }
}

BASE_URL = "https://hbgj.njuae.cn/base-business-api/api"


def _random_loc(cfg):
    if "longitude_range" in cfg:
        return {
            "longitude": str(round(random.uniform(*cfg["longitude_range"]), 6)),
            "latitude": str(round(random.uniform(*cfg["latitude_range"]), 6)),
            "address": cfg["address"]
        }
    return {"longitude": cfg["longitude"], "latitude": cfg["latitude"], "address": cfg["address"]}


def do_clock_in(token, location, clock_type):
    loc = _random_loc(LOCATIONS.get(location, LOCATIONS["兴化"]))
    payload = {
        "clockLongitude": loc["longitude"],
        "clockLatitude": loc["latitude"],
        "clockAddress": loc["address"],
        "clockType": clock_type
    }
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47"
    }
    resp = requests.post(f"{BASE_URL}/auth/b/clock", json=payload, headers=headers, timeout=20)
    data = resp.json()
    data["_loc"] = loc
    return data


def get_records(token, user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    headers = {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47"
    }
    params = {
        "clockUser": user_id,
        "beginClockTime": f"{today} 00:00:00",
        "endClockTime": f"{today} 23:59:59",
        "current": 1,
        "pageSize": 9999
    }
    resp = requests.get(f"{BASE_URL}/auth/b/clock", params=params, headers=headers, timeout=20)
    return resp.json()


class ClockInApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title="自动打卡", size=(400, 620))
        self.main_window.position = (60, 60)

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20, spacing=10))

        # Title
        main_box.add(toga.Label(
            "📋 自动打卡工具",
            style=Pack(font_size=24, font_weight="bold", text_align="center",
                       color="#667eea", padding=(0, 0, 10, 0))
        ))

        # Token
        main_box.add(toga.Label("授权码 (Token)", style=Pack(color="#555", font_size=13, padding=(10, 0, 4, 0))))
        self.token_input = toga.TextInput(
            placeholder="粘贴 Authorization Token",
            style=Pack(height=46, font_size=14, padding=8)
        )
        main_box.add(self.token_input)

        # Location
        main_box.add(toga.Label("打卡位置", style=Pack(color="#555", font_size=13, padding=(10, 0, 4, 0))))
        self.location_sel = toga.Selection(items=["兴化", "南大"], style=Pack(height=44))
        self.location_sel.selected = "兴化"
        main_box.add(self.location_sel)

        # Clock type
        main_box.add(toga.Label("打卡状态", style=Pack(color="#555", font_size=13, padding=(10, 0, 4, 0))))
        status_box = toga.Box(style=Pack(direction=ROW, spacing=10))
        self.clock_type_label = toga.Label("🏠 上班打卡", style=Pack(font_size=15, width=150))
        self.status_switch = toga.Switch(label="下班打卡", style=Pack(width=150), on_change=self._on_switch)
        status_box.add(self.clock_type_label)
        status_box.add(self.status_switch)
        main_box.add(status_box)

        # Submit button
        self.submit_btn = toga.Button(
            "🏃 提交打卡",
            on_press=self._on_submit,
            style=Pack(height=52, font_size=17, font_weight="bold",
                       background_color="#667eea", color="white",
                       margin=(16, 0, 0, 0))
        )
        main_box.add(self.submit_btn)

        # Records button
        self.records_btn = toga.Button(
            "📜 查看今日打卡记录",
            on_press=self._on_show_records,
            style=Pack(height=40, font_size=13, margin=(8, 0, 0, 0))
        )
        main_box.add(self.records_btn)

        # Result
        main_box.add(toga.Label("📦 返回结果", style=Pack(color="#555", font_size=13, padding=(16, 0, 4, 0))))
        self.result_text = toga.MultilineTextInput(
            style=Pack(height=160, font_size=12, readonly=True, padding=10),
            value="等待提交..."
        )
        main_box.add(self.result_text)

        self.main_window.content = main_box
        self.main_window.show()

    def _on_switch(self, widget):
        self.clock_type_label.text = "🏠 下班打卡" if widget.value else "🏠 上班打卡"

    def _on_submit(self, widget):
        token = self.token_input.value.strip()
        if not token:
            self._alert("⚠️ 提示", "请输入授权码！")
            return

        location = self.location_sel.selected or "兴化"
        clock_type = "2" if self.status_switch.value else "1"

        self.submit_btn.enabled = False
        self.submit_btn.label = "提交中..."
        self.result_text.value = "正在提交打卡请求...\n"
        self.result_text.readonly = False
        self.main_window.tick()

        try:
            result = do_clock_in(token, location, clock_type)
            loc = result.pop("_loc", {})
            self.result_text.value = json.dumps(result, indent=2, ensure_ascii=False)
            code = result.get("code", result.get("status", ""))
            msg = result.get("msg", result.get("message", ""))
            addr = loc.get("address", "")
            time_str = datetime.now().strftime("%H:%M:%S")
            info = f"📍 {addr}  ⏱ {time_str}\n"
            self.result_text.value = info + json.dumps(result, indent=2, ensure_ascii=False)
            if code == 200 or code == 0 or "成功" in str(msg):
                self._alert("✅ 打卡成功", msg or "打卡完成！")
            else:
                self._alert("❌ 打卡失败", f"{msg}\n\n{json.dumps(result, ensure_ascii=False)}")
        except Exception as e:
            self.result_text.value = f"❌ 异常：{e}"
            self._alert("❌ 错误", str(e))
        finally:
            self.submit_btn.enabled = True
            self.submit_btn.label = "🏃 提交打卡"
            self.result_text.readonly = True

    def _on_show_records(self, widget):
        token = self.token_input.value.strip()
        if not token:
            self._alert("⚠️ 提示", "请先输入授权码")
            return
        dialog = toga.TextInputDialog(
            title="查看打卡记录",
            message="请输入用户ID (User ID)：",
            initial_value="",
            on_result=self._on_records_result
        )
        dialog.show(self.main_window)

    def _on_records_result(self, dialog, user_id):
        if not user_id:
            return
        token = self.token_input.value.strip()
        try:
            data = get_records(token, user_id.strip())
            self.result_text.value = json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            self._alert("❌ 查询失败", str(e))

    def _alert(self, title, msg):
        d = toga.Dialog(title=title, message=msg, on_result=None)
        d.show(self.main_window)


def main():
    return ClockInApp("clockin", "com.example.clockin")
