Open python SDK for APIs

# steps to build wheel from source
python setup.py bdist_wheel

# steps to install
pip install wheel_path


*****************
HOW TO USE
*****************

import open_sdk.Client as Client

# pets Create
cl = Client('pets',
            token="yqa7ea1ok_QGiFV2cO49G6DH7gGV5ZCDqg2BPeuVupOQP90ZQQlxCh3ozzxSPc1IntWF9Koxqz9QH-h-35obYIdycLkzsdx2DJrifDFZf5YYdENJwef7s1EwhBtwCvsROm6UwuNcu7kGgQ")
cl.createPets()
