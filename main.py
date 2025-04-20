from src.alpha import Alpha
from src.memory import ChannelTypes

def main():
    alpha = Alpha()
    i = 0
    while alpha.memory.find_channel(ChannelTypes.console, i):
        i += 1
    alpha.set_channel(ChannelTypes.console, i)
    while True:
        req = input(f"In channel {alpha.current_channel} ")
        if req.startswith("channel"):
            alpha.set_channel(ChannelTypes.console, int(req.removeprefix("channel ")))
            print("Set channel " + req.removeprefix("channel "))
            continue
        answer = alpha.process_message(req.split(": ")[1], req.split(": ")[0])
        print(answer)

if __name__ == "__main__":
    main()