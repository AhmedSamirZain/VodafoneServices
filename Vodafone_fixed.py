import requests
import json
import os
import time

class VodafoneRed:
    def __init__(self, number, password):
        self.number = number
        self.password = password
        self.access_token = None
        self.req = requests.Session()

    def login(self):
        """تسجيل الدخول والحصول على توكن"""
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "silentLogin": "false",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "mobile.vodafone.com.eg",
            "User-Agent": "okhttp/4.11.0",
        }

        data = {
            "username": self.number,
            "password": self.password,
            "grant_type": "password",
            "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            "client_id": "ana-vodafone-app",
        }

        for attempt in range(3):
            try:
                print(f"\t[→] محاولة {attempt + 1} من 3...")
                response = self.req.post(url, headers=headers, data=data, timeout=30)
                result = response.json()

                if "access_token" in result:
                    self.access_token = result["access_token"]
                    print(f"\n\t[✅] تم تسجيل الدخول بنجاح للرقم {self.number}\n")
                    return True
                else:
                    print(f"\n\t[❌] فشل تسجيل الدخول: {result.get('error_description', 'بيانات غير صحيحة')}\n")
                    return False
            except Exception as e:
                print(f"\t[❌] محاولة {attempt + 1} فشلت: {e}")
                if attempt < 2:
                    print("\t[→] جاري إعادة المحاولة بعد 3 ثواني...")
                    time.sleep(3)
                else:
                    print("\n\t[❌] فشل الاتصال بعد 3 محاولات")
                    return False
        return False

    def get_headers(self, token=None, msisdn=None, additional_headers=None):
        """إنشاء الهيدرز الموحدة"""
        headers = {
            "Authorization": f"Bearer {token or self.access_token}",
            "api-version": "v2",
            "x-agent-operatingsystem": "16",
            "clientId": "AnaVodafoneAndroid",
            "x-agent-device": "Samsung SM-S938B",
            "x-agent-version": "2026.6.2",
            "x-agent-build": "1171",
            "msisdn": msisdn or self.number,
            "Accept": "application/json",
            "Accept-Language": "ar",
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "mobile.vodafone.com.eg",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "User-Agent": "okhttp/4.12.0"
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def choose_quota(self):
        """اختيار كمية التقسيم"""
        quotas = {
            "1": {"mi": "15000", "voice": "2000", "sms": "200", "desc": "15,000 ميجا - 2,000 دقيقة - 200 رسالة"},
            "2": {"mi": "25000", "voice": "2500", "sms": "200", "desc": "25,000 ميجا - 2,500 دقيقة - 200 رسالة"},
            "3": {"mi": "28000", "voice": "3000", "sms": "200", "desc": "28,000 ميجا - 3,000 دقيقة - 200 رسالة"},
            "4": {"mi": "30000", "voice": "3500", "sms": "200", "desc": "30,000 ميجا - 3,500 دقيقة - 200 رسالة"},
            "5": {"mi": "35000", "voice": "4500", "sms": "200", "desc": "35,000 ميجا - 4,500 دقيقة - 200 رسالة"},
            "6": {"mi": "40000", "voice": "6000", "sms": "200", "desc": "40,000 ميجا - 6,000 دقيقة - 200 رسالة"},
            "7": {"mi": "45000", "voice": "6000", "sms": "200", "desc": "45,000 ميجا - 6,000 دقيقة - 200 رسالة"},
            "8": {"mi": "50000", "voice": "7000", "sms": "200", "desc": "50,000 ميجا - 7,000 دقيقة - 200 رسالة"},
            "9": {"mi": "55000", "voice": "7000", "sms": "200", "desc": "55,000 ميجا - 7,000 دقيقة - 200 رسالة"},
            "10": {"mi": "60000", "voice": "8000", "sms": "200", "desc": "60,000 ميجا - 8,000 دقيقة - 200 رسالة"},
            "11": {"mi": "65000", "voice": "8000", "sms": "200", "desc": "65,000 ميجا - 8,000 دقيقة - 200 رسالة"},
            "12": {"mi": "75000", "voice": "9500", "sms": "200", "desc": "75,000 ميجا - 9,500 دقيقة - 200 رسالة"},
            "13": {"mi": "87000", "voice": "9950", "sms": "200", "desc": "87,000 ميجا - 9,950 دقيقة - 200 رسالة"},
            "14": {"mi": "110000", "voice": "10000", "sms": "200", "desc": "110,000 ميجا - 10,000 دقيقة - 200 رسالة"},
            "15": {"mi": "200000", "voice": "10300", "sms": "200", "desc": "200,000 ميجا - 10,300 دقيقة - 200 رسالة"},
            "16": {"mi": "250000", "voice": "20000", "sms": "200", "desc": "250,000 ميجا (250 جيجا) - 20,000 دقيقة - 200 رسالة"},
        }
        
        print("\n" + "=" * 70)
        print("\t\tاختر كمية التقسيم للعضو الجديد".center(70))
        print("=" * 70)
        print("\n  # |     الميجابايتس     |     الدقائق     |    الرسائل")
        print("-" * 70)
        
        for key, val in quotas.items():
            print(f"  {key.ljust(2)} | {val['mi'].rjust(15)}  | {val['voice'].rjust(15)}  | {val['sms'].rjust(10)}")
        
        print("\n" + "-" * 70)
        print("\t0. إدخال كمية مخصصة (Custom)")
        print("-" * 70)
        
        choice = input("\n\tاختر رقم (0-16): ").strip()
        
        if choice == "0":
            print("\n\t[→] أدخل الكميات المخصصة:")
            try:
                mi = input("\tالميجابايتس (مثال: 30000): ").strip()
                voice = input("\tالدقائق (مثال: 3000): ").strip()
                sms = input("\tالرسائل (مثال: 200): ").strip()
                
                if mi and voice and sms:
                    print(f"\n\t[✅] تم اختيار: {mi} ميجا، {voice} دقيقة، {sms} رسالة")
                    return mi, voice, sms
                else:
                    print("\t[!] بيانات غير صحيحة، سيتم استخدام القيم الافتراضية")
                    return "15000", "2000", "200"
            except:
                print("\t[!] خطأ في الإدخال، سيتم استخدام القيم الافتراضية")
                return "15000", "2000", "200"
        elif choice in quotas:
            return quotas[choice]["mi"], quotas[choice]["voice"], quotas[choice]["sms"]
        else:
            print("\t[!] اختيار غير صحيح، سيتم استخدام القيم الافتراضية (15,000 ميجا - 2,000 دقيقة)")
            return "15000", "2000", "200"

    def send_invitation(self):
        """إرسال دعوة"""
        print("\n" + "-" * 40)
        member2 = input("\tأدخل رقم العضو الثاني: ").strip()
        
        if not member2:
            print("\t[❌] الرقم لا يمكن أن يكون فارغاً")
            return

        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        
        headers = self.get_headers()
        headers.update({
            "device-id": "9837e2b64f728632",
            "x-agent-operatingsystem": "16"
        })
        
        data = {
            "category": [
                {"listHierarchyId": "PackageID", "value": "8804"},
                {"listHierarchyId": "TemplateID", "value": "880"},
                {"listHierarchyId": "TierID", "value": "8804"}
            ],
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "MI", "value": "5"},
                        {"characteristicName": "Voice", "value": "5"},
                        {"characteristicName": "extraMember", "value": "0"}
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"}
                ]
            },
            "type": "SendInvitation"
        }

        try:
            print("\t[→] جاري إرسال الدعوة...")
            response = self.req.post(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                print(f"\n\t[✅] تم إرسال الدعوة بنجاح إلى {member2}")
                try:
                    print(f"\t[→] الرد: {response.json()}")
                except:
                    pass
                return True
            else:
                print(f"\n\t[❌] فشل الإرسال - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(f"\t{response.text}")
                return False
        except Exception as e:
            print(f"\t[❌] خطأ: {e}")
            return False

    def accept_invitation_with_retry(self, member2, password2, max_retries=3, delay=5):
        """
        قبول دعوة مع إعادة المحاولة التلقائية
        """
        print(f"\n\t[→] بدء قبول الدعوة مع {max_retries} محاولات...")
        
        for attempt in range(1, max_retries + 1):
            print(f"\n\t{'='*40}")
            print(f"\t[→] محاولة قبول الدعوة رقم {attempt} من {max_retries}")
            print(f"\t{'='*40}")
            
            try:
                # 1. تسجيل دخول العضو الثاني
                url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
                headers_token = {
                    "Accept": "application/json, text/plain, */*",
                    "Connection": "keep-alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Host": "mobile.vodafone.com.eg",
                    "User-Agent": "okhttp/4.11.0",
                }
                data_token = {
                    "username": member2,
                    "password": password2,
                    "grant_type": "password",
                    "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
                    "client_id": "ana-vodafone-app",
                }

                print("\t[→] جاري تسجيل دخول الرقم الثاني...")
                res_token = requests.post(url_token, headers=headers_token, data=data_token, timeout=30)
                
                if res_token.status_code != 200:
                    print(f"\t[❌] فشل تسجيل الدخول - رمز الخطأ: {res_token.status_code}")
                    if attempt < max_retries:
                        print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                        time.sleep(delay)
                        continue
                    else:
                        print("\t[❌] تم استنفاذ جميع المحاولات")
                        return False
                
                token_data = res_token.json()
                
                if "access_token" not in token_data:
                    print(f"\t[❌] فشل تسجيل الدخول: {token_data.get('error_description', 'توكن غير موجود')}")
                    if attempt < max_retries:
                        print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                        time.sleep(delay)
                        continue
                    else:
                        print("\t[❌] تم استنفاذ جميع المحاولات")
                        return False

                token_member2 = token_data["access_token"]
                print("\t[✅] تم تسجيل دخول الرقم الثاني")

                # 2. قبول الدعوة
                url_accept = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
                
                headers_accept = self.get_headers(token=token_member2, msisdn=member2)
                headers_accept.update({
                    "x-agent-operatingsystem": "16",
                    "device-id": "9837e2b64f728632",
                    "api_id": "APP"
                })
                
                data_accept = {
                    "category": [
                        {"listHierarchyId": "TemplateID", "value": "880"}
                    ],
                    "name": "EnterpriseRedFamily",
                    "parts": {
                        "member": [
                            {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                            {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"}
                        ]
                    },
                    "type": "AcceptInvitation"
                }

                print("\t[→] جاري قبول الدعوة...")
                response = requests.patch(url_accept, headers=headers_accept, json=data_accept, timeout=30)
                
                if response.status_code in [200, 201]:
                    print(f"\n\t{'='*40}")
                    print(f"\t[✅] تم قبول الدعوة بنجاح في المحاولة رقم {attempt}")
                    print(f"\t{'='*40}")
                    try:
                        print(f"\t[→] الرد: {response.json()}")
                    except:
                        pass
                    return True
                else:
                    print(f"\t[❌] فشل قبول الدعوة - رمز الخطأ: {response.status_code}")
                    if response.text:
                        print(f"\t[→] رسالة الخطأ: {response.text[:200]}...")
                    
                    if attempt < max_retries:
                        print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                        time.sleep(delay)
                    else:
                        print("\t[❌] تم استنفاذ جميع المحاولات")
                        
            except requests.exceptions.Timeout:
                print(f"\t[❌] انتهت المهلة (Timeout)")
                if attempt < max_retries:
                    print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                    time.sleep(delay)
                else:
                    print("\t[❌] تم استنفاذ جميع المحاولات")
                    
            except requests.exceptions.ConnectionError:
                print(f"\t[❌] مشكلة في الاتصال بالإنترنت")
                if attempt < max_retries:
                    print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                    time.sleep(delay)
                else:
                    print("\t[❌] تم استنفاذ جميع المحاولات")
                    
            except Exception as e:
                print(f"\t[❌] خطأ غير متوقع: {e}")
                if attempt < max_retries:
                    print(f"\t[→] انتظار {delay} ثواني ثم المحاولة مرة أخرى...")
                    time.sleep(delay)
                else:
                    print("\t[❌] تم استنفاذ جميع المحاولات")
        
        return False

    def send_then_auto_accept(self):
        """إرسال دعوة ← انتظار 20 ثانية ← قبول تلقائي مع إعادة المحاولة"""
        print("\n" + "-" * 50)
        member2 = input("\tأدخل رقم العضو الثاني: ").strip()
        password2 = input("\tأدخل كلمة مرور الرقم الثاني: ").strip()
        
        if not member2 or not password2:
            print("\t[❌] الرقم وكلمة المرور مطلوبان")
            return

        # 1. إرسال دعوة
        print("\n\t[→] الخطوة 1: إرسال الدعوة")
        if not self.send_invitation_auto(member2):
            print("\t[❌] فشل إرسال الدعوة، لن يتم المتابعة")
            return

        # 2. انتظار 20 ثانية
        print("\n\t[→] الخطوة 2: انتظار 20 ثانية حتى تظهر الدعوة...")
        for i in range(20, 0, -1):
            print(f"\r\t[→] انتظار {i} ثانية...", end="")
            time.sleep(1)
        print("\n\t[✅] انتهى الانتظار")

        # 3. قبول الدعوة مع إعادة المحاولة التلقائية
        print("\n\t[→] الخطوة 3: قبول الدعوة مع إعادة المحاولة")
        success = self.accept_invitation_with_retry(
            member2=member2,
            password2=password2,
            max_retries=3,
            delay=5
        )
        
        if success:
            print("\n\t[✅] اكتملت العملية بنجاح ✅")
        else:
            print("\n\t[❌] فشلت العملية بعد 3 محاولات ❌")
            print("\t[→] تأكد من أن الدعوة لا تزال فعالة وأن الرقم الثاني صحيح")

    def send_invitation_auto(self, member2):
        """إرسال دعوة بدون تفاعل المستخدم"""
        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = self.get_headers()
        headers.update({
            "device-id": "9837e2b64f728632",
            "x-agent-operatingsystem": "16"
        })
        
        data_invite = {
            "category": [
                {"listHierarchyId": "PackageID", "value": "8804"},
                {"listHierarchyId": "TemplateID", "value": "880"},
                {"listHierarchyId": "TierID", "value": "8804"}
            ],
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "MI", "value": "5"},
                        {"characteristicName": "Voice", "value": "5"},
                        {"characteristicName": "extraMember", "value": "0"}
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"}
                ]
            },
            "type": "SendInvitation"
        }

        try:
            print("\t[→] جاري إرسال الدعوة...")
            response = self.req.post(url, headers=headers, json=data_invite)
            
            if response.status_code in [200, 201]:
                print(f"\t[✅] تم إرسال الدعوة بنجاح إلى {member2}")
                return True
            else:
                print(f"\t[❌] فشل إرسال الدعوة - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(f"\t{response.text}")
                return False
        except Exception as e:
            print(f"\t[❌] خطأ في الإرسال: {e}")
            return False

    def redistribute_quota(self, member2=None):
        """تقسيم الباقة"""
        if member2 is None:
            print("\n" + "-" * 40)
            member2 = input("\tأدخل رقم العضو الثاني: ").strip()
        
        if not member2:
            print("\t[❌] الرقم لا يمكن أن يكون فارغاً")
            return False

        mi, voice, sms = self.choose_quota()

        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        
        headers = self.get_headers()
        headers.update({
            "device-id": "9837e2b64f728632",
            "x-agent-operatingsystem": "16",
            "Connection": "close"
        })
        
        data = {
            "category": [
                {"listHierarchyId": "TemplateID", "value": "880"}
            ],
            "createdBy": {"value": "MobileApp"},
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "MI", "value": mi},
                        {"characteristicName": "Voice", "value": voice},
                        {"characteristicName": "SMS", "value": sms}
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"}
                ]
            },
            "type": "QuotaRedistribution"
        }

        for attempt in range(3):
            try:
                print(f"\t[→] جاري تقسيم الباقة... محاولة {attempt + 1} من 3")
                response = self.req.patch(url, headers=headers, json=data, timeout=30)
                
                if response.status_code in [200, 201]:
                    print(f"\n\t[✅] تم تقسيم الباقة بنجاح")
                    print(f"\t[→] {mi} ميجا، {voice} دقيقة، {sms} رسالة للرقم {member2}")
                    try:
                        print(f"\t[→] الرد: {response.json()}")
                    except:
                        pass
                    return True
                else:
                    print(f"\n\t[❌] فشل التقسيم - رمز الخطأ: {response.status_code}")
                    if response.text:
                        print(f"\t{response.text}")
                    return False
            except Exception as e:
                print(f"\t[❌] محاولة {attempt + 1} فشلت: {e}")
                if attempt < 2:
                    print("\t[→] جاري إعادة المحاولة بعد 3 ثواني...")
                    time.sleep(3)
                else:
                    print("\n\t[❌] فشل تقسيم الباقة بعد 3 محاولات")
                    return False
        return False

    def cancel_invitation(self, member2=None):
        """إلغاء دعوة / الخروج من الباقة"""
        if member2 is None:
            print("\n" + "-" * 40)
            member2 = input("\tأدخل رقم العضو (الذي تريد إخراجه): ").strip()
        
        if not member2:
            print("\t[❌] الرقم لا يمكن أن يكون فارغاً")
            return False

        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = self.get_headers()
        headers.update({
            "device-id": "9837e2b64f728632",
            "x-agent-operatingsystem": "16"
        })
        
        # نفس الـ payload اللي عندك مع تحديث TemplateID
        data = {
            "category": [
                {"listHierarchyId": "TemplateID", "value": "880"}  # تحديث لـ 880 بدلاً من 617
            ],
            "createdBy": {"value": "MobileApp"},
            "name": "EnterpriseRedFamily",  # تحديث الاسم
            "parts": {
                "member": [
                    {
                        "id": [{"schemeName": "MSISDN", "value": member2}],
                        "type": "Member"
                    },
                    {
                        "id": [{"schemeName": "MSISDN", "value": self.number}],
                        "type": "Owner"
                    }
                ]
            },
            "type": "CancelInvitation"
        }

        try:
            print("\t[→] جاري إخراج العضو من الباقة...")
            response = self.req.patch(url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                print(f"\n\t[✅] تم إخراج العضو {member2} من الباقة بنجاح")
                try:
                    print(f"\t[→] الرد: {response.json()}")
                except:
                    pass
                return True
            else:
                print(f"\n\t[❌] فشل الإخراج - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(f"\t{response.text}")
                return False
        except Exception as e:
            print(f"\t[❌] خطأ: {e}")
            return False

    def change_owner(self):
        """تغيير مالك الباقة"""
        print("\n" + "-" * 50)
        print("\t[⚠️] تحذير: تغيير المالك سيجعل الرقم الجديد هو المسؤول عن الباقة")
        print("\t[→] المالك الحالي: " + self.number)
        
        new_owner = input("\n\tأدخل الرقم الجديد (المالك الجديد): ").strip()
        new_owner_password = input("\tأدخل كلمة مرور المالك الجديد: ").strip()
        
        if not new_owner or not new_owner_password:
            print("\t[❌] الرقم وكلمة المرور مطلوبان")
            return False

        # 1. تسجيل دخول المالك الجديد
        print("\n\t[→] جاري تسجيل دخول المالك الجديد...")
        url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        headers_token = {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "mobile.vodafone.com.eg",
            "User-Agent": "okhttp/4.11.0",
        }
        data_token = {
            "username": new_owner,
            "password": new_owner_password,
            "grant_type": "password",
            "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            "client_id": "ana-vodafone-app",
        }

        try:
            res_token = requests.post(url_token, headers=headers_token, data=data_token, timeout=30)
            
            if res_token.status_code != 200:
                print(f"\t[❌] فشل تسجيل دخول المالك الجديد - رمز الخطأ: {res_token.status_code}")
                return False
            
            token_data = res_token.json()
            
            if "access_token" not in token_data:
                print(f"\t[❌] فشل تسجيل الدخول: {token_data.get('error_description', 'توكن غير موجود')}")
                return False

            token_new_owner = token_data["access_token"]
            print("\t[✅] تم تسجيل دخول المالك الجديد")

            # 2. تغيير المالك
            url_change = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
            
            headers_change = self.get_headers(token=token_new_owner, msisdn=new_owner)
            headers_change.update({
                "device-id": "9837e2b64f728632",
                "x-agent-operatingsystem": "16",
                "api_id": "APP"
            })
            
            # التأكد من وجود العضو القديم في الباقة
            print("\n\t[→] جاري تغيير المالك...")
            print(f"\t[→] المالك القديم: {self.number}")
            print(f"\t[→] المالك الجديد: {new_owner}")
            
            data_change = {
                "category": [
                    {"listHierarchyId": "TemplateID", "value": "880"}
                ],
                "createdBy": {"value": "MobileApp"},
                "parts": {
                    "member": [
                        {
                            "id": [{"schemeName": "MSISDN", "value": self.number}],
                            "type": "Member"  # المالك القديم يصبح عضو
                        },
                        {
                            "id": [{"schemeName": "MSISDN", "value": new_owner}],
                            "type": "Owner"   # المالك الجديد
                        }
                    ]
                },
                "type": "ChangeOwner"  # نوع العملية تغيير المالك
            }

            response = requests.patch(url_change, headers=headers_change, json=data_change, timeout=30)
            
            if response.status_code in [200, 201]:
                print(f"\n\t[✅] تم تغيير المالك بنجاح")
                print(f"\t[→] المالك الجديد: {new_owner}")
                print(f"\t[→] {self.number} أصبح عضواً")
                try:
                    print(f"\t[→] الرد: {response.json()}")
                except:
                    pass
                
                # تحديث رقم المالك في الجلسة الحالية
                self.number = new_owner
                return True
            else:
                print(f"\n\t[❌] فشل تغيير المالك - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(f"\t{response.text}")
                return False
                
        except Exception as e:
            print(f"\t[❌] خطأ: {e}")
            return False

    def accept_invitation(self):
        """قبول دعوة (يدوي)"""
        print("\n" + "-" * 40)
        member2 = input("\tأدخل رقم العضو الثاني (المرسل): ").strip()
        password2 = input("\tأدخل كلمة مرور الرقم الثاني: ").strip()
        
        if not member2 or not password2:
            print("\t[❌] الرقم وكلمة المرور مطلوبان")
            return

        success = self.accept_invitation_with_retry(
            member2=member2,
            password2=password2,
            max_retries=3,
            delay=5
        )
        
        if success:
            print("\n\t[✅] تم قبول الدعوة بنجاح ✅")
        else:
            print("\n\t[❌] فشل قبول الدعوة بعد 3 محاولات ❌")

    def redistribute_then_auto_cancel(self):
        """تقسيم ← انتظار 20 ثانية ← إلغاء تلقائي"""
        print("\n" + "-" * 50)
        member2 = input("\tأدخل رقم العضو الثاني: ").strip()
        
        if not member2:
            print("\t[❌] الرقم لا يمكن أن يكون فارغاً")
            return

        if not self.redistribute_quota(member2):
            return

        print("\t[→] انتظار 20 ثانية ثم إلغاء الدعوة تلقائياً...")
        for i in range(20, 0, -1):
            print(f"\r\t[→] انتظار {i} ثانية...", end="")
            time.sleep(1)
        print("\n\t[✅] انتهى الانتظار")
        
        if self.cancel_invitation(member2):
            print("\n\t[✅] اكتملت العملية بنجاح ✅")
        else:
            print("\n\t[❌] فشلت عملية الإلغاء ❌")

    def show_menu(self):
        """عرض القائمة الرئيسية"""
        while True:
            print("\n" + "=" * 60)
            print("\t\tالقائمة الرئيسية".center(60))
            print("=" * 60)
            print("\t1. إرسال دعوة فقط (Send Invitation)")
            print("\t2. قبول دعوة فقط (Accept Invitation)")
            print("\t3. تقسيم الباقة فقط (Quota Redistribution)")
            print("\t4. إخراج عضو من الباقة (Cancel/Exit)")
            print("\t5. إرسال → انتظار 20ث → قبول تلقائي (مع إعادة المحاولة)")
            print("\t6. تقسيم → انتظار 20ث → إلغاء تلقائي")
            print("\t7. تغيير مالك الباقة (Change Owner)")
            print("\t8. خروج (Exit)")
            print("=" * 60)
            
            choice = input("\tاختر رقم: ").strip()
            
            if choice == "1":
                self.send_invitation()
            elif choice == "2":
                self.accept_invitation()
            elif choice == "3":
                self.redistribute_quota()
            elif choice == "4":
                self.cancel_invitation()
            elif choice == "5":
                self.send_then_auto_accept()
            elif choice == "6":
                self.redistribute_then_auto_cancel()
            elif choice == "7":
                self.change_owner()
            elif choice == "8":
                print("\n\t[✅] مع السلامة!")
                break
            else:
                print("\t[❌] اختيار غير صحيح")
            
            if choice != "8":
                input("\n\t[→] اضغط Enter للمتابعة...")


if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("=" * 60)
    print("برنامج التحكم في مجموعة فودافون Red".center(60))
    print("=" * 60)
    
    number = input("\nأدخل رقم هاتفك (المالك): ").strip()
    password = input("أدخل كلمة المرور: ").strip()
    
    if not number or not password:
        print("\n[❌] الرقم وكلمة المرور مطلوبان!")
        time.sleep(2)
        exit()
    
    app = VodafoneRed(number, password)
    
    if app.login():
        app.show_menu()
    else:
        print("\n[❌] لا يمكن المتابعة بسبب فشل تسجيل الدخول.")
        time.sleep(2)