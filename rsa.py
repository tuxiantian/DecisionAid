from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# 生成RSA公私钥对
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# 私钥序列化并保存到PEM格式
pem_private_key = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)
# 将私钥写入本地文件
with open("private_key.pem", "wb") as private_key_file:
    private_key_file.write(pem_private_key)
print("私钥已写入 'private_key.pem' 文件中")

# 公钥序列化并保存到PEM格式
pem_public_key = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
# 将公钥写入本地文件
with open("public_key.pem", "wb") as public_key_file:
    public_key_file.write(pem_public_key)
print("公钥已写入 'public_key.pem' 文件中")

# 从文件中读取私钥
with open("private_key.pem", "rb") as private_key_file:
    loaded_private_key = serialization.load_pem_private_key(
        private_key_file.read(),
        password=None
    )
print("私钥从文件中加载成功")

# 从文件中读取公钥
with open("public_key.pem", "rb") as public_key_file:
    loaded_public_key = serialization.load_pem_public_key(
        public_key_file.read()
    )
print("公钥从文件中加载成功")

# 加密和解密测试
message = b"Hello, this is a secret message!"
ciphertext = loaded_public_key.encrypt(
    message,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
print("加密消息:", ciphertext)

plaintext = loaded_private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
print("解密消息:", plaintext.decode())
