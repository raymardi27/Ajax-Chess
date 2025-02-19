const lobbySocket = new WebSocket(
    (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/ws/lobby/'
);

lobbySocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    const event = data.event;

    if (event === 'online_users') {
        initializeOnlineUsers(data.usernames);
    } else if (event === 'user_join') {
        addUserToList(data.username);
    } else if (event === 'user_leave') {
        removeUserFromList(data.username);
    } else if (event === 'receive_invitation') {
        displayReceivedInvitation(data.from_username, data.game_id);
    } else if (event === 'invitation_revoked') {
        handleInvitationRevoked(data.game_id, data.to_username, data.from_username);
    } else if (event === 'invitation_accepted') {
        handleInvitationAccepted(data.game_id, data.to_username, data.from_username);
    } else if (event === 'invitation_declined') {
        handleInvitationDeclined(data.game_id, data.to_username);
    } else if (event === 'game_deleted') {
        handleGameDeleted(data.game_id, data.message);
    } else if (event === 'received_invitations') {
        initializeReceivedInvitations(data.invitations);
    } else if (event === 'sent_invitations') {
        initializeSentInvitations(data.invitations);
    }
};

lobbySocket.onclose = function(e) {
    console.error('Lobby Socket closed unexpectedly');
};

document.addEventListener('DOMContentLoaded', function() {
    // Refresh the page when the modal is closed
    $('#messageModal').on('hidden.bs.modal', function () {
        // Refresh the page
        location.reload();
    });
});

function initializeOnlineUsers(usernames) {
    const onlineUsersList = document.getElementById('onlineUsersList');
    onlineUsersList.innerHTML = '';  // Clear existing list
    usernames.forEach(function(username) {
        if (username !== window.username) {
            addUserToList(username);
        }
    });
}

function initializeReceivedInvitations(invitations) {
    const invitationList = document.getElementById('invitationList');
    invitationList.innerHTML = '';
    invitations.forEach(function(invitation) {
        displayReceivedInvitation(invitation.white_player__username, invitation.id);
    });
}

function initializeSentInvitations(invitations) {
    const sentInvitationsList = document.getElementById('sentInvitationsList');
    sentInvitationsList.innerHtml = '',
    invitations.forEach(function(invitation) {
        displaySentInvitation(invitation.black_player__username, invitation.id);
    })
}

function addUserToList(username) {
    const onlineUsersList = document.getElementById('onlineUsersList');
    const userItem = document.createElement('li');
    userItem.className = 'list-group-item d-flex justify-content-between align-items-center';
    userItem.id = 'user-' + username;
    userItem.textContent = username;

    // Add 'Challenge' button
    const challengeButton = document.createElement('button');
    challengeButton.className = 'btn btn-sm btn-primary';
    challengeButton.textContent = 'Challenge';
    challengeButton.onclick = function() {
        sendInvitation(username);
    };

    userItem.appendChild(challengeButton);
    onlineUsersList.appendChild(userItem);
}

function removeUserFromList(username) {
    const userItem = document.getElementById('user-' + username);
    if (userItem) {
        userItem.parentNode.removeChild(userItem);
    }
}

function sendInvitation(opponentUsername) {
    lobbySocket.send(JSON.stringify({
        'action': 'send_invitation',
        'opponent_username': opponentUsername,
    }));

    // Display Sent invitation
    const sentInvitationsList = document.getElementById('sentInvitationsList');
    const sentInvitationItem = document.createElement('li');
    sentInvitationItem.className = 'list-group-item';
    sentInvitationItem.id = 'sent-invitation-' + opponentUsername;
    sentInvitationItem.textContent = 'Challenge sent to ' + opponentUsername;

    // Revoke button
    const revokeButton = document.createElement('button');
    revokeButton.className = 'btn btn-sm btn-danger ms-2';
    revokeButton.textContent = 'Revoke';
    revokeButton.onclick = function() {
        revokeInvitation(opponentUsername);
    };

    sentInvitationItem.appendChild(revokeButton);
    sentInvitationsList.appendChild(sentInvitationItem);
}

function displayReceivedInvitation(fromUsername, gameId) {
    const invitationList = document.getElementById('invitationList');
    const invitationItem = document.createElement('li');
    invitationItem.className = 'list-group-item';
    invitationItem.id = 'invitation-' + gameId;
    invitationItem.textContent = 'Game invitation from ' + fromUsername;

    // Accept button
    const acceptButton = document.createElement('button');
    acceptButton.className = 'btn btn-sm btn-success ml-2';
    acceptButton.textContent = 'Accept';
    acceptButton.onclick = function() {
        respondInvitation(gameId, 'accept');
    };

    // Decline button
    const declineButton = document.createElement('button');
    declineButton.className = 'btn btn-sm btn-danger ml-2';
    declineButton.textContent = 'Decline';
    declineButton.onclick = function() {
        respondInvitation(gameId, 'decline');
    };

    invitationItem.appendChild(acceptButton);
    invitationItem.appendChild(declineButton);
    invitationList.appendChild(invitationItem);
}

function displaySentInvitation(opponentUsername, gameId) {
    const sentInvitationsList = document.getElementById('sentInvitationsList');
    const sentInvitationItem = document.createElement('li');
    sentInvitationItem.className = 'list-group-item';
    sentInvitationItem.id = 'sent-invitation-' + opponentUsername;
    sentInvitationItem.textContent = 'Challenge sent to ' + opponentUsername;

    // Revoke button
    const revokeButton = document.createElement('button');
    revokeButton.className = 'btn btn-sm btn-danger ms-2';
    revokeButton.textContent = 'Revoke';
    revokeButton.onclick = function() {
        revokeInvitation(opponentUsername);
    };

    sentInvitationItem.appendChild(revokeButton);
    sentInvitationsList.appendChild(sentInvitationItem);
}

function respondInvitation(gameId, response) {
    lobbySocket.send(JSON.stringify({
        'action': 'respond_invitation',
        'game_id': gameId,
        'response': response,
    }));

    // Remove the invitation from the list
    const invitationItem = document.getElementById('invitation-' + gameId);
    if (invitationItem) {
        invitationItem.parentNode.removeChild(invitationItem);
    }

    // Redirect
    if (response === 'accept'){
        window.location.href = '/game/' + gameId + '/';
    } else if (response === 'decline') {
        alert("You have declined the invitation");
    }
}

function revokeInvitation(opponentUsername){
    lobbySocket.send(JSON.stringify({
        'action': 'revoke_invitation',
        'opponent_username': opponentUsername,
    }));

    // Clear the sent invitations
    const sentInvitationItem = document.getElementById('sent-invitation-'+opponentUsername);
    if(sentInvitationItem) {
        sentInvitationItem.parentNode.removeChild(sentInvitationItem);
    }
}

function handleInvitationAccepted(gameId, from_username, to_username) {
    if (window.username === from_username || window.username === to_username) {
        // Redirect to the game page
        window.location.href = '/game/' + gameId + '/';
    }
}

function handleInvitationDeclined(gameId, opponentUsername) {
    // Notify the user that the invitation was declined
    showMessageModal(opponentUsername + ' has declined your invitation.');
    window.location.href = '/'
}

function handleInvitationRevoked(gameId, to_username, from_username) {

    if (window.username === from_username){
        
        const sentInvitationItem = document.getElementById('sent-invitation-' + to_username);
        if(sentInvitationItem) {
            sentInvitationItem.parentNode.removeChild(sentInvitationItem);
        }

    } else if (window.username === to_username) {
        // Remove the invitation from the list
        const invitationItem = document.getElementById('invitation-' + gameId);
        if (invitationItem) {
            invitationItem.parentNode.removeChild(invitationItem);
        }
        showMessageModal(from_username + ' has revoked their challenge.');
    }

    
}

function handleGameDeleted(game_id, message) {
    showMessageModal("Game Deleted", message);

    // Remove the game
    const gameRow = document.getElementById('game-row-' + game_id);
    if(gameRow) {
        gameRow.parentNode.removeChild(gameRow);
    }
    
}

function showMessageModal(title, message) {
    document.getElementById('messageModalTitle').textContent = title;
    document.getElementById('messageModalBody').textContent = message;
    $('#messageModal').modal('show');
}

