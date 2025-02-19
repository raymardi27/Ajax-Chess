




$('#logoutButton').on('click', function() {
    clearInterval(fetchAvailableUsers);
});


// setInterval(updateGame, 10000);  // Poll every 1 second



// function movePiece() {
//   const source = document.getElementById("source").value;
//   const destination = document.getElementById("destination").value;
//   const sourcePiece = document.getElementById(source).innerHTML;
//   document.getElementById(source).innerHTML = "&nbsp;";
//   document.getElementById(destination).innerHTML = sourcePiece;
// }

// function resetBoard() {
//   window.location.reload();
// }
