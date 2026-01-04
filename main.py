from Alice import Alice
api_key = "sk-eca32ece6ecc4f3ebace6fd5805e7e2c"

if __name__ == "__main__":
    from Agent.QwenClient import QwenClient

    client = QwenClient(api_key)

    alice = Alice(api_key=api_key, client=client)

    while True:
        user_input = input("你: ")
        if user_input.lower() == "退出":
            print("再见！")
            break
        response = alice.respond([user_input])
        print("爱丽丝: " + response)