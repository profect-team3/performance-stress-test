from locust import HttpUser, task, between, SequentialTaskSet
import random
import string
import uuid

# --- 전역 변수: 모든 가상 사용자가 공유할 고정된 데이터 ---
GLOBAL_MENU_PRICE = 17000

# --- Helper Functions for Data Generation ---
def random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choices(letters, k=length))

def random_phone_number():
    return f"010{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}"

# --- Customer Workflow (이전 코드와 동일) ---
class CustomerWorkflow(SequentialTaskSet):
    def on_start(self):
        self.store_id = None
        self.menu_id = None
        self.menu_price = None
        self.cart_quantity = 0 
        self.address_id = None
        self.cart_total = 0

    @task
    def add_address(self):
        payload = {
            "alias": "My Home",
            "address": str({uuid.uuid4().hex[:12]}),
            "addressDetail": "Apt 101",
            "isDefault": "true"
        }
        with self.client.post("/user/user/address/add", json=payload, name="Customer: Add Address", catch_response=True) as response:
            if response.ok:
                self.address_id = response.json().get("result", {}).get("address_id")
                if self.address_id:
                    response.success()
                else:
                    response.failure("Address ID not found in response")
            else:
                response.failure(f"Failed to add address: {response.text}")
    
    @task
    def get_stores_and_select_menu(self):
        # 글로벌 storeId와 menuId 사용
        self.store_id = '5d55692d-4573-4c7a-9ae5-c9d211b3e80b'
        self.menu_id = '202943ac-7a28-4909-acce-e2f86c2eb5a2'
        
        # 가게 조회
        with self.client.get("/store/store/customer", name="Customer: Get Stores", catch_response=True) as response:
            if not response.ok:
                response.failure(f"Failed to get stores: {response.text}")
                self.interrupt()
                return
            response.success()

        # 메뉴 조회
        with self.client.get(f"/store/store/menu/{self.store_id}", name="Customer: Get Menus", catch_response=True) as response:
            if not response.ok:
                response.failure(f"Failed to get menus: {response.text}")
                self.interrupt()
                return
            result = response.json().get("result", {})
            menus = result.get("content", [])
            if menus:
                # 글로벌 menuId에 맞는 메뉴 찾기
                for menu in menus:
                    if menu.get("menuId") == self.menu_id:
                        self.menu_price = menu.get("price", 0)
                        break
                else:
                    response.failure("Global menu not found in store")
                    self.interrupt()
                    return
            else:
                response.failure("No menus available")
                self.interrupt()
                return
            response.success()
    
    @task
    def add_item_to_cart(self):
        if not self.menu_id or not self.store_id:
            return
        self.cart_quantity += 1
        payload = {
            "menuId": self.menu_id,
            "storeId": self.store_id,
            "quantity": 1
        }
        self.client.post("/order/order/item", json=payload, name="Customer: Add Cart Item")

    @task
    def get_cart_total(self):
        with self.client.get("/order/order/cart", name="Customer: Get Cart", catch_response=True) as response:
            if response.ok:
                cart_data = response.json().get("result", [])
                if isinstance(cart_data, list) and cart_data:
                    # 메뉴 가격 정보를 얻기 위해 메뉴 조회
                    menu_prices = {}
                    with self.client.get(f"/store/store/menu/{self.store_id}", name="Customer: Get Menus for Price", catch_response=True) as menu_response:
                        if menu_response.ok:
                            menu_result = menu_response.json().get("result")
                            menus = menu_result.get("content")
                            for menu in menus:
                                menu_prices[menu.get("menuId")] = menu.get("price", 0)
                        else:
                            response.failure(f"Failed to get menus for price: {menu_response.text}")
                            return
                    
                    # 장바구니 리스트에서 첫 번째 아이템의 menuId와 quantity를 가져옴
                    item = cart_data[0]
                    self.menu_id = item.get("menuId")
                    self.cart_quantity = item.get("quantity", 0)
                    # 총액 계산 (메뉴 가격 사용)
                    self.cart_total = sum(menu_prices.get(item.get("menuId"), 0) * item.get("quantity", 0) for item in cart_data if isinstance(item, dict))
                elif isinstance(cart_data, dict):
                    self.cart_total = cart_data.get("totalPrice", 0)
                else:
                    self.cart_total = 0
                response.success()
            else:
                response.failure(f"Failed to get cart: {response.text}")
                self.cart_total = 0

    @task
    def create_order(self):
        if not self.cart_quantity > 0 or not self.cart_total:
            print("Debug: Skipping order creation due to invalid cart data")  # 디버깅용
            return
        
        payload = {
            "paymentMethod": "CREDIT_CARD",
            "orderChannel": "ONLINE",
            "receiptMethod": "DELIVERY",
            "requestMessage": "Locust test order",
            "totalPrice": self.cart_total,
            "deliveryAddress": "123 Main St, Apt 101"
        }
        with self.client.post("/order/order", json=payload, name="Customer: Create Order", catch_response=True) as response:
            if response.ok:
                response.success()
            else:
                response.failure(f"Failed to create order: {response.text}")

# --- Owner Workflow (가게 생성 시나리오) ---
class OwnerWorkflow(SequentialTaskSet):
    def on_start(self):
        self.store_id = None  # 생성한 가게 ID 저장
        self.menu_id = "202943ac-7a28-4909-acce-e2f86c2eb5a2"
    @task
    def create_store(self):
        payload = {
            "storeName": f"Locust Store {uuid.uuid4().hex[:12]}",
            "regionId": "3bf1fca4-32b4-45b7-bf99-1822aefcec7a",
            "categoryId": "6530a750-89b7-44af-aebc-0e008fbeccd7",
            "desc": "A great store for testing.",
            "address": "123 Locust St.",
            "phoneNumber": random_phone_number(),
            "minOrderAmount": 10000
        }
        with self.client.post("/store/store/owner", json=payload, name="Owner: Create Store", catch_response=True) as res:
            if res.ok:
                self.store_id = res.json().get("result", {}).get("storeId")
                res.success()
            else:
                res.failure(f"Owner: Failed to create store: {res.text}")

    @task
    def create_menu(self):
        if not self.store_id:
            return
        payload = {
            "storeId": self.store_id,
            "name": f"Locust Menu {uuid.uuid4().hex[:12]}",
            "price": GLOBAL_MENU_PRICE,
            "description": "Test menu for Locust."
        }
        with self.client.post("/store/store/owner/menu", json=payload, name="Owner: Create Menu", catch_response=True) as res:
            if res.ok:
                self.menu_id = res.json().get("result", {}).get("menuId")
                res.success()
            else:
                res.failure(f"Failed to create menu: {res.text}")

    @task
    def update_menu_stock(self):
        if not self.menu_id:
            return
        payload = {
            "menuId": self.menu_id,
            "quantity": 100
        }
        with self.client.put("/store/store/owner/menu/stock", json=payload, name="Owner: Update Menu Stock", catch_response=True) as res:
            if res.ok:
                res.success()
            else:
                res.failure(f"Failed to update menu stock: {res.text}")

class CustomerUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [CustomerWorkflow]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        self.signup_and_login(role="CUSTOMER")
        if not self.token:
            # 로그인 실패 시 tasks를 비우는 대신, 
            # tasks가 None이거나 비어있지 않도록
            # Locust의 on_start 내에서 작업을 중단시킵니다.
            self.stop(reason="Login failed for CustomerUser")

    def signup_and_login(self, role="CUSTOMER"):
        self.username = f"{role.lower()}_{random_string(8)}_{uuid.uuid4().hex[:6]}"
        self.email = f"{self.username}@example.com"
        self.password = "password123!"
        
        signup_payload = {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "nickname": random_string(8),
            "realName": role.capitalize(),
            "phoneNumber": random_phone_number(),
            "userRole": role
        }
        self.client.post("/user/user/signup", json=signup_payload, name="Customer: Signup")
        
        login_payload = {"username": self.username, "password": self.password}
        with self.client.post("/auth/auth/login", json=login_payload, name="Customer: Login", catch_response=True) as response:
            if response.ok:
                self.token = response.json().get("result", {}).get("accessToken")
                if self.token:
                    self.client.headers["Authorization"] = f"Bearer {self.token}"
                    response.success()
                else:
                    response.failure(f"Customer login successful but no accessToken found for {self.username}")
            else:
                response.failure(f"Customer login failed for {self.username}: {response.text}")

# --- OwnerUser 클래스 ---
class OwnerUser(HttpUser):
    wait_time = between(5, 10)
    tasks = [OwnerWorkflow]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None

    def on_start(self):
        self.signup_and_login(role="OWNER")
        if not self.token:
            # 로그인 실패 시 tasks를 비우는 대신,
            # 작업을 중단시킵니다.
            self.stop(reason="Login failed for OwnerUser")

    def signup_and_login(self, role="OWNER"):
        self.username = f"{role.lower()}_{random_string(8)}_{uuid.uuid4().hex[:6]}"
        self.email = f"{self.username}@example.com"
        self.password = "password123!"
        
        signup_payload = {
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "nickname": random_string(8),
            "realName": role.capitalize(),
            "phoneNumber": random_phone_number(),
            "userRole": role
        }
        self.client.post("/user/user/signup", json=signup_payload, name="Owner: Signup")
        
        login_payload = {"username": self.username, "password": self.password}
        with self.client.post("/auth/auth/login", json=login_payload, name="Owner: Login", catch_response=True) as response:
            if response.ok:
                self.token = response.json().get("result", {}).get("accessToken")
                if self.token:
                    self.client.headers["Authorization"] = f"Bearer {self.token}"
                    response.success()
                else:
                    response.failure(f"Owner login successful but no accessToken found for {self.username}")
            else:
                response.failure(f"Owner login failed for {self.username}: {response.text}")