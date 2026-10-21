from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Rectangle
from kivy.metrics import dp
from kivy.core.text import LabelBase
from plyer import gps
from geopy.geocoders import Nominatim
import math, os

# 注册中文字体
LabelBase.register(name="SimHei", fn_regular=r"C:/Windows/Fonts/simhei.ttf")
FONT_CN = "SimHei"
geolocator = Nominatim(user_agent="gps_calc_app")

# ==========业务函数：球面距离计算==========
def haversine_distance(lat1, lon1, alt1, lat2, lon2, alt2):
    R = 6371000  #地球半径，单位米
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat/2)**2 + math.cos(lat1_r)*math.cos(lat2_r)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    flat_distance = R * c
    alt_diff = alt2 - alt1
    total_dist = math.sqrt(flat_distance**2 + alt_diff**2)
    return round(total_dist, 2)

class RootLayout(FloatLayout):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.point_list = []      #临时历史点位（最多10个）
        self.collect_lib = []     #独立收藏库，无数量上限

        # =====背景图=====
        with self.canvas.before:
            self.bg = Rectangle(source="", pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        bg_file = "earth_bg.jpg"
        if os.path.exists(bg_file):
            self.bg.source = bg_file
        else:
            print(f"警告：找不到背景图片 {bg_file}，请放到py同目录")

        # 主垂直布局
        main_box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10),
                             size_hint=(0.96,0.96), pos_hint={"center_x":0.5,"center_y":0.5})

        # 标题
        title = Label(text="高精度坐标距离计算器", font_name=FONT_CN, font_size=dp(22),
                      size_hint_y=None, height=dp(44), color=(1,1,1,1))
        main_box.add_widget(title)

        # 【地址输入框，支持手动修改】
        self.addr_input = TextInput(hint_text="地址（定位后自动填充，可手动修改）", font_name=FONT_CN, font_size=dp(14), size_hint_y=None, height=dp(40))
        main_box.add_widget(self.addr_input)

        # 输入行：纬度、经度、高度
        input_row = BoxLayout(spacing=dp(8),size_hint_y=None,height=dp(44))
        self.lat_input = TextInput(hint_text="纬度", font_name=FONT_CN, input_filter="float", font_size=dp(14))
        self.lon_input = TextInput(hint_text="经度", font_name=FONT_CN, input_filter="float", font_size=dp(14))
        self.alt_input = TextInput(hint_text="高度m", font_name=FONT_CN, input_filter="float", font_size=dp(14))
        input_row.add_widget(self.lat_input)
        input_row.add_widget(self.lon_input)
        input_row.add_widget(self.alt_input)
        main_box.add_widget(input_row)

        # 按钮行：自动定位，添加坐标
        btn_row = BoxLayout(spacing=dp(10),size_hint_y=None,height=dp(44))
        btn_loc = Button(text="自动定位", font_name=FONT_CN, on_press=self.get_gps)
        btn_add = Button(text="添加坐标", font_name=FONT_CN, on_press=self.add_point)
        btn_row.add_widget(btn_loc)
        btn_row.add_widget(btn_add)
        main_box.add_widget(btn_row)

        # =========临时历史点位区域（最多10个）=========
        label_history = Label(text="【临时点位列表】最多10个，勾选自动计算", font_name=FONT_CN,
                              size_hint_y=None, height=dp(26), color=(1,1,1,1))
        main_box.add_widget(label_history)
        scroll_temp = ScrollView(size_hint_y=0.22)
        self.temp_layout = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.temp_layout.bind(minimum_height=self.temp_layout.setter('height'))
        scroll_temp.add_widget(self.temp_layout)
        main_box.add_widget(scroll_temp)

        # =========独立收藏库区域=========
        label_collect = Label(text="【收藏库】永久保存点位", font_name=FONT_CN,
                              size_hint_y=None, height=dp(26), color=(1,1,1,1))
        main_box.add_widget(label_collect)
        scroll_collect = ScrollView(size_hint_y=0.22)
        self.collect_layout = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        self.collect_layout.bind(minimum_height=self.collect_layout.setter('height'))
        scroll_collect.add_widget(self.collect_layout)
        main_box.add_widget(scroll_collect)

        # 计算结果提示
        self.result_label = Label(text="添加点位，勾选两点自动计算距离",
                                  font_name=FONT_CN, font_size=dp(15),
                                  color=(1,1,1,1),size_hint_y=None,height=dp(36))
        main_box.add_widget(self.result_label)

        self.add_widget(main_box)

    def update_bg(self,*args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    # GPS定位
    def get_gps(self,instance):
        try:
            gps.configure(on_location=self.on_gps_loc)
            gps.start(minTime=1000, minDistance=1)
            self.result_label.text="正在获取GPS..."
        except Exception as e:
            self.result_label.text = f"定位失败:{str(e)}"

    def on_gps_loc(self,**kwargs):
        lat = kwargs['lat']
        lon = kwargs['lon']
        alt = kwargs.get('alt',0)
        self.lat_input.text=str(lat)
        self.lon_input.text=str(lon)
        self.alt_input.text=str(alt)
        # 反向解析地址
        try:
            location = geolocator.reverse(f"{lat},{lon}")
            self.addr_input.text = location.address
        except Exception:
            self.addr_input.text = "地址解析失败"
        self.result_label.text="定位+地址获取成功！"

    # 添加临时点位，最多10个
    def add_point(self,instance):
        if len(self.point_list) >= 10:
            self.result_label.text="⚠️临时点位上限为10个！请删除旧点再添加"
            return
        try:
            lat = float(self.lat_input.text)
            lon = float(self.lon_input.text)
            alt = float(self.alt_input.text)
            addr = self.addr_input.text.strip()
            idx = len(self.point_list)
            self.point_list.append( {"lat":lat,"lon":lon,"alt":alt,"addr":addr,"checked":False} )
            self.refresh_temp_list()
            self.result_label.text="✅临时点位添加成功"
        except:
            self.result_label.text="输入错误，请输入数字"

    def refresh_temp_list(self):
        self.temp_layout.clear_widgets()
        for i,p in enumerate(self.point_list):
            line_box = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(32))
            cb = CheckBox(active=p["checked"])
            cb.bind(active=lambda c,v,ii=i: self.on_temp_check(ii, v))
            txt_label = Label(text=f"点{i+1} | {p['lat']},{p['lon']},{p['alt']}m | {p['addr'][:20]}", font_name=FONT_CN, color=(1,1,1,1))
            btn_collect = Button(text="收藏", font_name=FONT_CN, size_hint_x=0.16, on_press=lambda x,ii=i:self.save_to_collect(ii))
            btn_del = Button(text="删除", font_name=FONT_CN, size_hint_x=0.16, on_press=lambda x,ii=i:self.del_temp_point(ii))
            line_box.add_widget(cb)
            line_box.add_widget(txt_label)
            line_box.add_widget(btn_collect)
            line_box.add_widget(btn_del)
            self.temp_layout.add_widget(line_box)
        self.auto_calc()

    def on_temp_check(self, index, value):
        self.point_list[index]["checked"] = value
        self.auto_calc()

    def save_to_collect(self, temp_idx):
        p = self.point_list[temp_idx]
        new_item = dict(p)
        new_item["checked"] = False
        self.collect_lib.append(new_item)
        self.refresh_collect_list()
        self.result_label.text="✅已存入收藏库"

    def refresh_collect_list(self):
        self.collect_layout.clear_widgets()
        for i,p in enumerate(self.collect_lib):
            line_box = BoxLayout(spacing=dp(6), size_hint_y=None, height=dp(32))
            cb = CheckBox(active=p["checked"])
            cb.bind(active=lambda c,v,ii=i: self.on_collect_check(ii, v))
            txt_label = Label(text=f"收藏{i+1}|{p['lat']},{p['lon']},{p['alt']}m | {p['addr'][:20]}", font_name=FONT_CN, color=(1,1,1,1))
            btn_del = Button(text="移除", font_name=FONT_CN, size_hint_x=0.18, on_press=lambda x,ii=i:self.del_collect_point(ii))
            line_box.add_widget(cb)
            line_box.add_widget(txt_label)
            line_box.add_widget(btn_del)
            self.collect_layout.add_widget(line_box)
        self.auto_calc()

    def on_collect_check(self, index, value):
        self.collect_lib[index]["checked"] = value
        self.auto_calc()

    def del_temp_point(self,index):
        self.point_list.pop(index)
        self.refresh_temp_list()
        self.result_label.text="临时点已删除"

    def del_collect_point(self,index):
        self.collect_lib.pop(index)
        self.refresh_collect_list()
        self.result_label.text="收藏点已移除"

    # 自动计算：合并临时列表+收藏库里面所有勾选的点
    def auto_calc(self):
        checked = []
        for p in self.point_list:
            if p["checked"]:
                checked.append(p)
        for p in self.collect_lib:
            if p["checked"]:
                checked.append(p)
        if len(checked) < 2:
            self.result_label.text="勾选至少2个点位（临时/收藏库都可以）自动计算"
            return
        p1 = checked[0]
        p2 = checked[1]
        dist = haversine_distance(p1["lat"],p1["lon"],p1["alt"], p2["lat"],p2["lon"],p2["alt"])
        self.result_label.text=f"✅两点空间距离 = {dist} 米"

class GpsCalcApp(App):
    def build(self):
        return RootLayout()

if __name__ == "__main__":
    GpsCalcApp().run()
