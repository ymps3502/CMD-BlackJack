import sys
import os
import socket
import select
from random import shuffle
from collections import deque

HOST = ''
SOCKET_LIST = []
USER_LIST = []
SOCKET_DICT = dict()
RECV_BUFFER = 4096
PORT = 9009
SERVER_STATE = "lobby"

PLAYER_LIST = []
DEALER_TURN = False
ROUND = 0
DECK = []
DEALER_HAND = []
NEXT_PLAYER = False


class user:
    """docstring for player"""

    def __init__(self, sock, name, state):
        self.sock = sock
        self.name = name
        self.state = state
        self.handcard = []


def chat_server():
    os.system('clear')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    # add server socket object to the list of readable connections
    SOCKET_LIST.append(server_socket)

    print "Chat server started on port " + str(PORT)

    while 1:

        # get the list sockets which are ready to be read through select
        # 4th arg, time_out  = 0 : poll and never block
        ready_to_read, ready_to_write, in_error = select.select(
            SOCKET_LIST, [], [], 0)

        for sock in ready_to_read:
            # a new connection request recieved
            if sock == server_socket:
                sockfd, addr = server_socket.accept()
                SOCKET_LIST.append(sockfd)
                SOCKET_DICT[str(sockfd.getpeername())] = 0
                print "Client (%s, %s) connected" % addr
            # a message from a client, not a new connection
            else:
                # process data recieved from client,
                try:
                    # receiving data from the socket.
                    data = sock.recv(RECV_BUFFER)
                    if data and SOCKET_DICT[str(sock.getpeername())] == 1:
                        u = [x for x in USER_LIST if x.sock == sock][0]
                        # there is something in the socket
                        if data == 'bj\n' and u.state == "lobby":
                            if SERVER_STATE == "playing":
                                u.state = "next"
                                sock.send("Please wait for the next game...\n")
                            else:
                                u.state = "playing"
                                if u not in PLAYER_LIST:
                                    PLAYER_LIST.append(u)
                                blackjack(u, 'bj')
                                dealerturn()
                                alllose()
                            if u not in PLAYER_LIST:
                                PLAYER_LIST.append(u)
                        elif u.state == "playing":
                            blackjack(u, data[:-1])
                            dealerturn()
                            alllose()
                        elif u.state == "waiting":
                            sock.send("Please wait for your turn...\n")
                        elif u.state == "next":
                            sock.send("Please wait for the next game...\n")
                        elif data == '!q\n':
                            u.state = "lobby"
                            u.sock.send = "Back to chatting room...\n"
                            print u.name + "leave the game\n"
                            PLAYER_LIST.remove(u)
                        elif u.state == "newgame":
                            u.state = "playing"
                            blackjack(u, 'bj')
                            dealerturn()
                            alllose()
                        else:
                            data = "\r" + u.name + ": " + data
                            broadcast(
                                server_socket, sock,
                                data)
                            print data
                    elif SOCKET_DICT[str(sock.getpeername())] == 0:
                        SOCKET_DICT[str(sock.getpeername())] = 1
                        USER_LIST.append(user(sock, data, "lobby"))
                        broadcast(
                            server_socket,
                            sock,
                            "\r%s entered our chatting room\n" % data)
                        print "\r%s entered our chatting room\n" % data
                    else:
                        # remove the socket that's broken
                        if sock in SOCKET_LIST:
                            SOCKET_LIST.remove(sock)

                        # at this stage,
                        # no data means probably the connection has been broken
                        broadcast(
                            server_socket, sock,
                            "\rClient (%s, %s) is offline\n" % addr)
                        print "\rClient (%s, %s) is offline\n" % addr

                # exception
                except socket.error:
                    broadcast(
                        server_socket,
                        sock,
                        "\rClient (%s, %s) is offline\n" % addr)
                    print "\rClient (%s, %s) is offline\n" % addr
                    continue

        global NEXT_PLAYER
        if NEXT_PLAYER:
            for player in PLAYER_LIST:
                if player.state == "playing":
                    NEXT_PLAYER = False
                    blackjack(player, "")
        if DEALER_TURN:
            for player in PLAYER_LIST:
                blackjack(player, "")
            for player in PLAYER_LIST:
                player.sock.send("Enter '!q' to quit or continuing the game\n")
            resetgame()

    server_socket.close()


def broadcast(server_socket, sock, message):
    # broadcast chat messages to all connected clients
    for s in SOCKET_LIST:
        # send the message only to peer
        if s != server_socket and s != sock:
            try:
                s.send(message)
            except socket.error:
                # broken socket connection
                s.close()
                # broken socket, remove it
                if s in SOCKET_LIST:
                    SOCKET_LIST.remove(s)


def blackjack(user, recv_msg):
    global DECK, DEALER_HAND, ROUND, DEALER_TURN, SERVER_STATE
    SERVER_STATE = "playing"
    if user.state == "next":
        return
    if ROUND == 0:
        DECK = [[i] for i in range(52)]
        shuffle(DECK)
        DECK = deque(DECK)
    while len(DEALER_HAND) < 2:
        DEALER_HAND.extend(DECK.popleft())
        ROUND = ROUND + 1
        print "Dealer's hand: %s\n" % handcard2string(0, DEALER_HAND)
    j = 0
    for i, player in enumerate(PLAYER_LIST):
        if player.state == "playing" and j == 0:
            j = j + 1
        elif player.state == "playing":
            player.state = "waiting"
        while len(user.handcard) < 2:
            user.handcard.extend(DECK.popleft())
    if user.state == "playing":
        msg = "Dealer's hand: %s\n" % handcard2string(1, DEALER_HAND)
        if recv_msg in ('y', 'Y', 'bj', ''):
            if recv_msg in ('y', 'Y'):
                user.handcard.extend(DECK.popleft())
            msg += "Your hand: %s\n" % handcard2string(0, user.handcard)
            if checkhand(user.handcard) > 21:
                msg += "You lose!\nPlease wait for the next game\n"
                user.state = "next"
                nextplayer(user)
            else:
                msg += "Do you want to hit? (y/n)\n"
            sendcardmsg(user, msg)
        elif recv_msg in ('n', 'N'):
            user.state = "waiting"
            nextplayer(user)
    if DEALER_TURN:
        while checkhand(DEALER_HAND) < 17:
            DEALER_HAND.extend(DECK.popleft())
        msg = "Dealer's hand: " + handcard2string(0, DEALER_HAND) + \
            "\n" + "Your hand: " + handcard2string(0, user.handcard) + "\n"
        if (checkhand(user.handcard) > checkhand(DEALER_HAND) or
                checkhand(DEALER_HAND) > 21):
            msg += "You win!!!\n"
        else:
            msg += "You lose!\n"
        sendcardmsg(user, msg)


def sendcardmsg(user, message):
    try:
        user.sock.send(message)
    except socket.error:
        # broken socket connection
        user.sock.close()
        # broken socket, remove it
        if user.sock in SOCKET_LIST:
            SOCKET_LIST.remove(user.sock)
        if user in PLAYER_LIST:
            PLAYER_LIST.remove(user)


def nextplayer(user):
    try:
        if PLAYER_LIST[PLAYER_LIST.index(user) + 1].state == "waiting":
            PLAYER_LIST[PLAYER_LIST.index(user) + 1].state = "playing"
            global NEXT_PLAYER
            NEXT_PLAYER = True
    except Exception:
        pass


def checkhand(handcard):
    '''
    color = 0 is spades, 1 is hearts, 2 is diamonds, 3 is clubs
    '''
    total = 0
    spadesA = False
    for card in handcard:
        color = card / 13
        number = card % 13 + 1 if card % 13 < 10 else 10
        if color == 0 and number == 1:
            spadesA = True
        total = total + number
    if total > 21 and spadesA:
        total = total - 10
    return total


def handcard2string(hide, handcard):
    cardstr = ""
    for i, card in enumerate(handcard):
        color = card / 13 + 1
        number = card % 13 + 1
        if hide == 1 and i == 0:
            cardstr = cardstr + "(??, ??), "
        else:
            cardstr = cardstr + "(" + str(color) + ", " + str(number) + "), "
    return cardstr[:-2]


def dealerturn():
    global PLAYER_LIST, DEALER_TURN
    for player in PLAYER_LIST:
        if player.state not in ("waiting", "next"):
            return
    DEALER_TURN = True


def alllose():
    global PLAYER_LIST
    for player in PLAYER_LIST:
        if player.state != "next":
            return
    resetgame()


def resetgame():
    global DEALER_HAND, ROUND, DEALER_TURN, PLAYER_LIST, SERVER_STATE
    for player in PLAYER_LIST:
        del player.handcard[:]
        player.state = "newgame"
    ROUND = 0
    del DEALER_HAND[:]
    DEALER_TURN = False
    SERVER_STATE = "newgame"


if __name__ == "__main__":
    sys.exit(chat_server())
