import ctypes
import random
from socketserver import BaseRequestHandler, UDPServer
import struct


#import time
datatype='I H H'
data_format = struct.Struct(datatype)
ack_pack=43690
acktype='I H H'
ack_format = struct.Struct(acktype)
max_seq=10
MSS=1000


#SERVERIP="192.168.1.23"
SERVERIP = ""
count=0
exp_seq=0
cur_seq=-1
p=0.05
#client_address=(socket.gethostname(),8000)

def cal_checksum(data):
    checksum = 0
    for i in range(0, len(data), 2):
        msg = str(data)
        word = ord(msg[i]) + (ord(msg[i+1]) << 8)
        carry = checksum + word
        checksum = (carry & 0xffff)+(carry >> 16)
    return (~ checksum) & 0xffff

#ack=1
class DataHandler(BaseRequestHandler):
    def handle(self):
        global count,datatype
        global data_format
        global ack_format,ack_pack,acktype,exp_seq,cur_seq
        #print('Got connection from', self.client_address)
        # Get message and client socket

        with open('yourfile.pdf','ba') as f:
            msg, sock = self.request          
            tup=data_format.unpack_from(msg[0:data_format.size], 0) 
            #print ("Received: ",tup[0])           
            if( p*100 >= random.randint(1, 100)):
                print("packet lost,sequence number = ",tup[0])
                return
            
            csum = cal_checksum(msg[data_format.size:])
            if(csum!=tup[1]):
                print("Check sum Error")
                return
            #if packet as expected sequence number increase seqnumber to next
            if(tup[0]==exp_seq):
                cur_seq=exp_seq
                f.write(msg[data_format.size:])
                exp_seq=(exp_seq+1)%(max_seq+1)
            else:
                return
            #print("recieved seq: ",tup[0])
            ack_num=cur_seq
            if(ack_num<0):
                ack_num=max_seq                   
            values = (ack_num,0,ack_pack)
            buf = ctypes.create_string_buffer(ack_format.size)
            ack_format.pack_into(buf, 0, *values)
            sock.sendto(buf,self.client_address)
            #print ("Ack Sent:",ack_num)
        
if __name__ == '__main__':
    print("Listening")
    serv = UDPServer((SERVERIP, 7735), DataHandler)
    serv.serve_forever()