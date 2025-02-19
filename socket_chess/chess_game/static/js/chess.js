let gameSocket = null;
let userTurn = null;

function connectToGame(gameId) {
    gameSocket = new WebSocket(
        (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/game/' + gameId + '/'
    );

    gameSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        if (data.event === 'game_state') {
            initializeBoard(data.board_html, data.user_turn, data.move_history, data.opponent_username, data.current_turn);
        } else if (data.event === 'move') {
            updateGameBoard(data.board_html, data.user_turn, data.move_history);
            if (data.game_over) {
                const outcome_message = data.outcome === 'tie' ? "Draw" : data.outcome === 'white_win' ? "White wins!" : "Black Wins!"
                showModal('Game Over' , 'Outcome: ' + outcome_message);

            }
        } else if (data.event === 'game_over') {
            updateGameBoard(data.board_html, data.user_turn, data.move_history);
            showModal('Game Over', data.message);

        } else if (data.event === 'error') {
            alert(data.message);
        }
    };

    gameSocket.onclose = function(e) {
        console.error('Game socket closed unexpectedly');
    };
}

function sendMove(move) {
    if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
        gameSocket.send(JSON.stringify({
            'move' : move
        }));
    }
}

function resignGame() {
    if (gameSocket && gameSocket.readyState === WebSocket.OPEN) {
        gameSocket.send(JSON.stringify({
            'resign' : true
        }));
    }
}

function initializeBoard(boardHtml, isUserTurn,moveHistory, opponentUsername, currentTurn) {
    const gameContainer = document.getElementById('game-container')
    gameContainer.innerHTML = boardHtml;
    userTurn = isUserTurn;
    toggleMoveInput(userTurn);
    updateMoveHistory(moveHistory);

    const opponentName = document.getElementById('opponent-name');
    if(opponentName){
        opponentName.innerHTML = 'Playing against: ' + opponentUsername;
    }

    const playingas = document.getElementById('playing-as');
    if(playingas) {
        const playas = isUserTurn ? 'White' : 'Black'
        playingas.innerHTML = `You are ${playas}`;
    }
    updateTurnIndicator(currentTurn)
}

function updateGameBoard(boardHtml, isUserTurn, moveHistory) {
    const gameContainer = document.getElementById('game-container');
    gameContainer.innerHTML = boardHtml;
    userTurn = isUserTurn;
    toggleMoveInput(userTurn);
    updateMoveHistory(moveHistory);
}

function toggleMoveInput(isUserTurn) {
    const moveForm = document.getElementById('moveForm');
    if (moveForm) {
        if (isUserTurn) {
            moveForm.style.display = 'block';
        } else {
            moveForm.style.display = 'none';
        }
    }
}

function updateMoveHistory(moveHistory) {
    const moveHistoryContainer = document.getElementById('move-history');
    if (moveHistoryContainer) {
        moveHistoryContainer.textContent = 'Moves: ' + moveHistory;
    }
}

function updateTurnIndicator(currentTurn) {
    const turnIndicator = document.getElementById('turn-indicator');
    if(turnIndicator) {
        const turn = currentTurn === window.username? "Your turn": currentTurn;
        turnIndicator.innerHTML = 'Current Turn: ' + turn;
    }
}

function showModal(title, message) {
    // Assuming you're using Bootstrap modals
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').textContent = message;
    $('#myModal').modal('show');
}

// Event listener for move submission
document.addEventListener('DOMContentLoaded', function() {
    const moveForm = document.getElementById('moveForm');
    if (moveForm) {
        moveForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const moveInput = document.getElementById('moveInput');
            const move = moveInput.value.trim();
            if (move.length === 4) {
                sendMove(move);
                moveInput.value = '';
            } else {
                showModal('Error', 'Invalid move format. Move should be in the format "e2e4".');
            }
        });
    }
});

// Event listener for modal buttons
const homeButton = document.getElementById('homePage');

if (homeButton) {
    homeButton.addEventListener('click',function() {
        window.location.href = '/'
    });
}
