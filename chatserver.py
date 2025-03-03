import socket
import json
import select
import threading
from typing import Dict, Tuple, Any

class StatusBroadcaster:
    def __init__(self, host: str = '0.0.0.0', port: int = 41234):
        self.host = host
        self.port = port
        # Create separate sockets for UDP and TCP
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients: Dict[str, Dict[str, Any]] = {}  # Store client info
    
    def start(self):
        """Start both UDP and TCP servers"""
        self.udp_socket.bind((self.host, self.port))
        self.tcp_socket.bind((self.host, self.port + 1))  # Use different port for TCP
        self.tcp_socket.listen(5)
        
        print(f"UDP server listening on {self.host}:{self.port}")
        print(f"TCP server listening on {self.host}:{self.port + 1}")
        
        try:
            while True:
                # Use select to monitor both sockets
                readable, _, _ = select.select([self.udp_socket, self.tcp_socket], [], [])
                
                for sock in readable:
                    if sock is self.udp_socket:
                        # Handle UDP message
                        data, addr = sock.recvfrom(1024)
                        self.handle_udp_message(data, addr)
                    else:
                        # Handle new TCP connection
                        client_sock, addr = sock.accept()
                        # Start a new thread for each TCP connection
                        threading.Thread(target=self.handle_tcp_connection, args=(client_sock, addr)).start()
                        
        except KeyboardInterrupt:
            print("Shutting down server...")
        finally:
            self.udp_socket.close()
            self.tcp_socket.close()
    
    def handle_udp_message(self, data: bytes, addr: Tuple[str, int]):
        """Process incoming UDP messages - Only for status updates"""
        try:
            message = data.decode('utf-8')
            client_key = f"udp_{addr[0]}:{addr[1]}"
            
            if message.startswith('REGISTER:'):
                # Register a new client for status updates
                username = message.split(':', 1)[1]
                self.clients[client_key] = {
                    'username': username, 
                    'status': 'online', 
                    'addr': addr,
                    'protocol': 'udp'
                }
                print(f"UDP client registered for status updates: {username} at {addr[0]}:{addr[1]}")
                
            elif message.startswith('STATUS:'):
                # Update client status
                self.handle_status_update(message, client_key)
                
        except Exception as e:
            print(f"Error handling UDP message: {e}")
    
    def handle_tcp_connection(self, client_sock: socket.socket, addr: Tuple[str, int]):
        """Handle TCP connection for chat messages"""
        try:
            while True:  # Keep connection alive to receive multiple messages
                data = client_sock.recv(1024)
                if not data:
                    break  # Client disconnected
                    
                message = data.decode('utf-8')
                client_key = f"tcp_{addr[0]}:{addr[1]}"
                
                if message.startswith('REGISTER:'):
                    username = message.split(':', 1)[1]
                    self.clients[client_key] = {
                        'username': username, 
                        'status': 'online', 
                        'socket': client_sock,
                        'addr': addr,
                        'protocol': 'tcp'
                    }
                    print(f"TCP client registered for chat: {username} at {addr[0]}:{addr[1]}")
                
                elif message.startswith('CHAT:'):
                    # Handle chat messages
                    _, username, chat_message = message.split(':', 2)
                    self.broadcast_chat(username, chat_message, client_key)
                    
        except Exception as e:
            print(f"Error handling TCP connection: {e}")
        finally:
            client_sock.close()
            if client_key in self.clients:
                del self.clients[client_key]
    
    def handle_status_update(self, message: str, client_key: str):
        """Handle status updates from both UDP and TCP clients"""
        status = message.split(':', 1)[1]
        
        if client_key in self.clients:
            self.clients[client_key]['status'] = status
            username = self.clients[client_key]['username']
            print(f"Status update from {username}: {status}")
            
            # Broadcast status change to all other clients
            self.broadcast_status(username, status, client_key)
    
    def broadcast_chat(self, username: str, message: str, exclude_client: str):
        """Send chat messages to all TCP clients except the sender"""
        chat_message = f"CHAT:{username}:{message}".encode('utf-8')
        
        for client_key, client_info in self.clients.items():
            if client_key != exclude_client and client_info['protocol'] == 'tcp':
                try:
                    client_info['socket'].send(chat_message)
                except Exception as e:
                    print(f"Error sending to {client_key}: {e}")
                    client_info['socket'].close()
                    del self.clients[client_key]
    
    def broadcast_status(self, username: str, status: str, exclude_client: str):
        """Send status updates to all UDP clients except the sender"""
        status_update = f"STATUS:{username}:{status}".encode('utf-8')
        
        for client_key, client_info in self.clients.items():
            if client_key != exclude_client and client_info['protocol'] == 'udp':
                try:
                    self.udp_socket.sendto(status_update, client_info['addr'])
                except Exception as e:
                    print(f"Error sending to {client_key}: {e}")
                    del self.clients[client_key]
    

if __name__ == "__main__":
    broadcaster = StatusBroadcaster()
    broadcaster.start()