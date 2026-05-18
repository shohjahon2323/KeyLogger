import asyncio
import random
import time
from termcolor import colored

class C2Server:
    def __init__(self, port=1337):
        self.port = port
        self.active_bots = []
        self.is_running = False

    async def start(self):
        self.is_running = True
        print(colored(f"[+] C2 Server initialized on port {self.port}. Waiting for connections...", 'green'))
        await self.simulate_botnet_traffic()

    async def simulate_botnet_traffic(self):
        while self.is_running:
            # Simulate bot connecting
            if random.random() > 0.7:
                bot_ip = f"192.168.1.{random.randint(2, 254)}"
                self.active_bots.append(bot_ip)
                print(colored(f"[*] New bot connected from {bot_ip} (Total: {len(self.active_bots)})", 'blue'))
            
            # Simulate heartbeat
            if len(self.active_bots) > 0 and random.random() > 0.5:
                bot = random.choice(self.active_bots)
                print(colored(f"[~] Received heartbeat from {bot}", 'dark_grey'))

            await asyncio.sleep(random.randint(1, 4))

    def broadcast_payload(self, command):
        print(colored(f"[!] Broadcasting command '{command}' to {len(self.active_bots)} nodes.", 'red', attrs=['bold']))
        time.sleep(1)
        print(colored("[+] Payload delivered successfully.", 'green'))

if __name__ == "__main__":
    print(colored("""
    ======================================
    [ C2 NODE - BOTNET COMMAND & CONTROL ]
    ======================================
    """, 'red', attrs=['bold']))
    server = C2Server()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n[-] Shutting down C2 server...")
