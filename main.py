from src.alpha import Alpha
from src.memory import ChannelTypes

def main():
    alpha = Alpha()
    alpha.set_channel(ChannelTypes.console, 0)
    while True:
        answer = alpha.process_message(input(">> "), "DVD")
        print(answer)

if __name__ == "__main__":
    main()