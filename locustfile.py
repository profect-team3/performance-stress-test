from locust import HttpUser, task, between, SequentialTaskSet
import random
import string
import uuid

# --- Helper Functions for Data Generation ---
def random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choices(letters, k=length))

def random_phone_number():
    return f"010{random.randint(1000, 9999):04d}{random.randint(1000, 9999):04d}"

# --- 전역 변수: 모든 가상 사용자가 공유할 고정된 데이터 ---
GLOBAL_STORE_ID = '3bf1fca4-32b4-45b7-bf99-1822aefcec7a'
GLOBAL_MENU_ID = '328f4218-0213-442e-855b-1cae0e3d706a'
GLOBAL_MENU_PRICE = 7000

# --- Customer Workflow (이전 코드와 동일) ---
class CustomerWorkflow(SequentialTaskSet):
    def on_start(self):
        self.store_id = GLOBAL_STORE_ID
        self.menu_id = GLOBAL_MENU_ID
        self.menu_price = GLOBAL_MENU_PRICE
        self.cart_quantity = 0 
        self.address_id = None

    @task
    def add_address(self):
        payload = {
            "alias": "My Home",
            "address": str({uuid.uuid4().hex[:12]}),
            "addressDetail": "Apt 101",
            "isDefault": "true"
        }
        with self.client.post("/api/customer/address/add", json=payload, name="Customer: Add Address", catch_response=True) as response:
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
        with self.client.get("/api/customer/store", name="Customer: Get Stores", catch_response=True) as response:
            if not response.ok:
                response.failure(f"Failed to get stores: {response.text}")
                self.interrupt()
                return

        with self.client.get(f"/api/menu/store/menu?storeId={self.store_id}", name="Customer: Get Menus", catch_response=True) as response:
            if not response.ok:
                response.failure(f"Failed to get menus: {response.text}")
                self.interrupt()
                return
    
    @task
    def add_item_to_cart(self):
        self.cart_quantity += 1
        payload = {
            "menuId": self.menu_id,
            "storeId": self.store_id,
            "quantity": 1
        }
        self.client.post("/api/customer/cart/item", json=payload, name="Customer: Add Cart Item")

    @task
    def create_order(self):
        if not self.cart_quantity > 0:
            return
        
        total_price = self.menu_price * self.cart_quantity
        payload = {
            "paymentMethod": "CREDIT_CARD",
            "orderChannel": "ONLINE",
            "receiptMethod": "DELIVERY",
            "requestMessage": "Locust test order",
            "totalPrice": total_price,
            "deliveryAddress": "123 Main St, Apt 101"
        }
        with self.client.post("/api/order", json=payload, name="Customer: Create Order", catch_response=True) as response:
            if response.ok:
                response.success()
            else:
                response.failure(f"Failed to create order: {response.text}")

# --- Owner Workflow (가게 생성 시나리오) ---
class OwnerWorkflow(SequentialTaskSet):
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
        with self.client.post("/api/store", json=payload, name="Owner: Create Store", catch_response=True) as res:
            if res.ok:
                store_id = res.json().get("result", {}).get("storeId")
                res.success()
            else:
                res.failure(f"Owner: Failed to create store: {res.text}")
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
        self.client.post("/api/user/signup", json=signup_payload, name="Customer: Signup")
        
        login_payload = {"username": self.username, "password": self.password}
        with self.client.post("/api/user/login", json=login_payload, name="Customer: Login", catch_response=True) as response:
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
        self.client.post("/api/user/signup", json=signup_payload, name="Owner: Signup")
        
        login_payload = {"username": self.username, "password": self.password}
        with self.client.post("/api/user/login", json=login_payload, name="Owner: Login", catch_response=True) as response:
            if response.ok:
                self.token = response.json().get("result", {}).get("accessToken")
                if self.token:
                    self.client.headers["Authorization"] = f"Bearer {self.token}"
                    response.success()
                else:
                    response.failure(f"Owner login successful but no accessToken found for {self.username}")
            else:
                response.failure(f"Owner login failed for {self.username}: {response.text}")