import socket
import threading
import sys
from typing import Optional, Tuple
import pyfiglet

class ChatClient:
    def __init__(self, host: str = '10.30.6.4', port: int = 41234):
        self.host = host
        self.port = port
        self.username: Optional[str] = None
        
        # Create UDP socket for status updates
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create TCP socket for chat
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def start(self, username: str):
        """Start the client with both UDP and TCP connections"""
        self.username = username
        
        try:
            # Connect TCP socket
            self.tcp_socket.connect((self.host, self.port + 1))
            
            # Register on both protocols
            self.udp_socket.sendto(f"REGISTER:{username}".encode('utf-8'), (self.host, self.port))
            self.tcp_socket.send(f"REGISTER:{username}".encode('utf-8'))
            
            # Start listener threads
            udp_thread = threading.Thread(target=self.listen_udp)
            tcp_thread = threading.Thread(target=self.listen_tcp)
            input_thread = threading.Thread(target=self.handle_user_input)
            
            udp_thread.daemon = True
            tcp_thread.daemon = True
            input_thread.daemon = True
            
            udp_thread.start()
            tcp_thread.start()
            input_thread.start()
            
            # Keep main thread alive
            udp_thread.join()
            tcp_thread.join()
            input_thread.join()
            
        except Exception as e:
            print(f"Error starting client: {e}")
            self.cleanup()
    
    def listen_udp(self):
        """Listen for status updates from other users"""
        try:
            while True:
                data, _ = self.udp_socket.recvfrom(1024)
                message = data.decode('utf-8')
                
                if message.startswith('STATUS:'):
                    _, username, status = message.split(':', 2)
                    if username != self.username:
                        print(f"\n[STATUS] {username} is now {status}")
                        print("Your message: ", end='', flush=True)
                        
        except Exception as e:
            print(f"UDP listener error: {e}")
    
    def listen_tcp(self):
        """Listen for chat messages from other users"""
        try:
            while True:
                data = self.tcp_socket.recv(1024)
                if not data:
                    break
                    
                message = data.decode('utf-8')
                if message.startswith('CHAT:'):
                    _, username, chat_message = message.split(':', 2)
                    if username != self.username:
                        print(f"\n[CHAT] {username}: {chat_message}")
                        print("Your message: ", end='', flush=True)
                else:
                    # Handle ASCII art messages
                    print(f"\n[ASCII ART] {message}")
                    print("Your message: ", end='', flush=True)
                        
        except Exception as e:
            print(f"TCP listener error: {e}")
            self.cleanup()
    
    def handle_user_input(self):
        """Handle user input for status updates and chat messages"""
        try:
            while True:
                message = input("Your message: ")
                
                if message.lower().startswith('/ascii'):
                    # send ascii
                    text = message[7:]
                    self.send_ascii(text)

                if message.lower().startswith('/status '):
                    # Send status update
                    status = message[8:]  # Remove '/status '
                    self.update_status(status)
                    
                elif message.lower() in ['/quit', '/exit']:
                    self.cleanup()
                    sys.exit(0)
                    
                else:
                    # Send chat message
                    self.send_chat(message)
                    
        except KeyboardInterrupt:
            self.cleanup()
            sys.exit(0)
    
    def update_status(self, status: str):
        """Send status update via UDP"""
        try:
            self.udp_socket.sendto(f"STATUS:{status}".encode('utf-8'), (self.host, self.port))
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def send_chat(self, message: str):
        """Send chat message via TCP"""
        try:
            self.tcp_socket.send(f"CHAT:{self.username}:{message}".encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def send_ascii(self, message: str):
        """ Send Ascii"""
        try:
            self.tcp_socket.send(f"ASCII:{message}".encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def cleanup(self):
        """Clean up sockets"""
        self.tcp_socket.close()
        self.udp_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python chatclient.py <username>")
        sys.exit(1)
        
    username = sys.argv[1]
    client = ChatClient()
    client.start(username)
