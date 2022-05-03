$("#start-button").on("click", function () {
	send("reset");
});

$("#yellow-team-controller").change(function () {
	let value = $(this).val();
	send("set_controller", {team: "Y", controller: value});
});

$("#blue-team-controller").change(function () {
	let value = $(this).val();
	send("set_controller", {team: "B", controller: value});
});

$("#check_timer").on("change", function () {
	send("set_check_timer", {enabled: this.checked});
});

$("#check_progress").on("change", function () {
	send("set_check_progress", {enabled: this.checked});
});

$("#check_goal").on("change", function () {
	send("set_check_goal", {enabled: this.checked});
});

$("#check_robots_in_penalty_area").on("change", function () {
	send("set_check_robots_in_penalty_area", {enabled: this.checked});
});

$("#save-state-button").on("click", function () {
	send("save_state");
});

$("#restore-state-button").on("click", function () {
	send("restore_state");
});

$("#randomize-ball-button").on("click", function () {
	send("randomize_ball");
});

$("#move-out-button").on("click", function () {
	send("move_out");
});

let snapshot = null;
let editing = null;
["ball-x", "ball-y",
"Y1-x", "Y1-y", "Y1-a",
"Y2-x", "Y2-y", "Y2-a",
"Y3-x", "Y3-y", "Y3-a",
"B1-x", "B1-y", "B1-a",
"B2-x", "B2-y", "B2-a",
"B3-x", "B3-y", "B3-a",].forEach(id => {
	let $el = $("#" + id);
	$el.on("focus", function () { editing = this; });
	$el.on("blur", function () { editing = null; });
	$el.on("keydown", function (evt) {
		/*
		NOTE(Richo): If the user presses either Enter (13) or Tab (9) the "move"
		command is sent	to the simulator.
		*/
		if (13 == evt.keyCode || 9 == evt.keyCode) {
			let value = parseFloat(this.innerText);
			if (isFinite(value)) {
				let parts = id.split("-");
				let object_key = parts[0].toUpperCase();
				let property = parts[1];
				send("move_object", {object: object_key, property: property, value: value});
			}
		}
		/*
		NOTE(Richo): Additionally, if the user presses Enter (13) we prevent the
		default event behavior and blur the input to simulate a "submit" event
		*/
		if (13 == evt.keyCode) {
			evt.preventDefault();
			$el.blur();
		}
	});
});

window.onload = function() {
	if (window.webots) {
		window.robotWindow = webots.window();
		window.robotWindow.setTitle('Fútbol de Robots!');
		window.robotWindow.receive = function (str) {
			let json = JSON.parse(str);
			let msg = json["msg"];
			let args = json["args"];
			if (msg == undefined) return;
			receive(msg, args);
		};
	} else {
		// HACK(Richo): Mock to test without webots
		window.robotWindow = {
			send: function (data) {
				console.log("SEND: " + data);
			}
		};
	}

	window.addEventListener("resize", resizeMessages);
	resizeMessages();
	startStepping();
	send("setup");
};

function resizeMessages() {
	let container = document.getElementById("main-container");
	let controls = document.getElementById("controls");
	let table = document.getElementById("table-display");
	let messages = document.getElementById("messages");
	
	var h = (container.clientHeight - controls.clientHeight - table.clientHeight) * 0.7;
	if (h < 0) { h = 0; }

	messages.style.height = "" + h + "px";
}


function startStepping() {
	setInterval(update, 128);
  }

function delay(ms) {
	return new Promise(resolve => {
		setTimeout(resolve, ms);
	})
}

let dispatchTable = {
	alert: function (data) {
		if (data.message) { alert(data.message); }
	},
	log: function (data){
		if (data.message) { console.log(data.message); }
	},
	update_controllers_list: function (data) {
		let selects = {
			Y: $("#yellow-team-controller"),
			B: $("#blue-team-controller")
		};
		Object.keys(selects).forEach(team => {
			let select = selects[team];
			select.html("");
			data.controllers
				.map(c => $("<option>").text(c).attr("value", c))
				.forEach(option => select.append(option));
			select.val(data[team]);
		});
	},
	update_flags: function (data) {
		$("#check_timer").get(0).checked = data["check_timer"];
		$("#check_progress").get(0).checked = data["check_progress"];
		$("#check_goal").get(0).checked = data["check_goal"];
		$("#check_robots_in_penalty_area").get(0).checked = data["check_robots_in_penalty_area"];
	},
	update: function (data) {
		if (snapshot) { // Preserve pending messages
			data.messages = snapshot.messages.concat(data.messages);
		}
		snapshot = data;
	},
	game_over: function () {
		$("#goal-panel").hide();
		$("#game-over-panel").show();
	},
};

function update () {
	if (!snapshot) return;
	let data = snapshot;
	
	if (data["messages"].length > 0) {
		while (data["messages"].length > 0) {
			let msg = data["messages"].shift();
			$("#messages").append($("<div>").text(msg));			
		}

		// Scroll to bottom
		let panel = $("#messages").get(0);
		panel.scrollTop = panel.scrollHeight - panel.clientHeight;
	}

	let fmt = (val) => val.toFixed(3);
	let degrees = (radians) => radians * (180/Math.PI);
	let update = (selector, text) => {
		let $el = $(selector);
		if ($el.get(0) == editing) {
			$el.css("color", "blue");
		} else {
			$el.css("color", "inherit");
			$el.text(text);
		}
	}

	$("#time-display").text(data["time"].toFixed(3) + "s");

	update("#ball-x", fmt(data["ball_translation"][0]));
	update("#ball-y", fmt(data["ball_translation"][1]));
	$("#ball-display").css("color", (data["selected"] == "BALL" ? "red" : "black"));

	Object.keys(data["robot_translation"]).forEach(robot_name => {
		let pos = data["robot_translation"][robot_name];
		let rot = data["robot_rotation"][robot_name];
		update("#" + robot_name + "-x", fmt(pos[0]));
		update("#" + robot_name + "-y", fmt(pos[1]));
		update("#" + robot_name + "-a", fmt(degrees(rot[2]*rot[3])) + "deg");
		$("#" + robot_name + "-display").css("color", (data["selected"] == robot_name ? "red" : "black"));
	});

	if(data["goal"]) {
		$("#goal-panel").show();
	} else {
		$("#goal-panel").hide();
	}
}

function receive (msg, args) {
	let fn = dispatchTable[msg];
	if (!fn) {
		console.error("Unknown message: " + msg);
	} else {
		fn(args);
	}
}

function send(msg, args) {
	let message = JSON.stringify({ msg: msg, args: args || {}, response_id: null });
	window.robotWindow.send(message);
}

/*
NOTE(Richo): Requests are messages that expect a response. I use the same dispatchTable
to register the response callback with a random id. The response id is sent as the last
parameter of the message. After the response is received I remove the key from the
dispatch table.
*/
function request(msg, args) {
	return new Promise((resolve, reject) => {
		let response_id;
		do { response_id =  Math.floor(Math.random() * Math.pow(2, 64)); }
		while (dispatchTable[response_id] != undefined);

		dispatchTable[response_id] = function (path) {
			delete dispatchTable[response_id];
			resolve(path);
		}
		let message = JSON.stringify({ msg: msg, args: args || {}, response_id: response_id });
		window.robotWindow.send(message);
	});
}
