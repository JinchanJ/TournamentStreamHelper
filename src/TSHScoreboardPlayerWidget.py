import os
import traceback
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import uic
import json
from .Helpers.TSHCountryHelper import TSHCountryHelper
from .StateManager import StateManager
from .TSHGameAssetManager import TSHGameAssetManager
from .TSHPlayerDB import TSHPlayerDB
from .TSHTournamentDataProvider import TSHTournamentDataProvider


class TSHScoreboardPlayerWidgetSignals(QObject):
    characters_changed = pyqtSignal()


class TSHScoreboardPlayerWidget(QGroupBox):
    countries = None
    countryModel = None
    characterModel = None

    signals = TSHScoreboardPlayerWidgetSignals()

    def __init__(self, index=0, teamNumber=0, path="", *args):
        super().__init__(*args)

        self.path = path

        self.index = index
        self.teamNumber = teamNumber

        self.losers = False

        uic.loadUi("src/layout/TSHScoreboardPlayer.ui", self)

        self.character_container = self.findChild(QWidget, "characters")

        self.LoadCountries()

        self.character_elements = []

        bottom_buttons_layout = QHBoxLayout()
        bottom_buttons_layout.setSpacing(4)
        self.layout().addLayout(bottom_buttons_layout, 99, 0, 1, 3)

        self.save_bt = QPushButton("Save new player")
        self.save_bt.font().setPointSize(10)
        # self.save_bt.setFont(self.parent.font_small)
        self.save_bt.setIcon(QIcon('assets/icons/save.svg'))
        bottom_buttons_layout.addWidget(self.save_bt)
        self.save_bt.clicked.connect(self.SavePlayerToDB)
        self.findChild(QLineEdit, "name").textChanged.connect(
            self.ManageSavePlayerToDBText)
        self.findChild(QLineEdit, "team").textChanged.connect(
            self.ManageSavePlayerToDBText)

        self.delete_bt = QPushButton("Delete player entry")
        # self.delete_bt.setFont(self.parent.font_small)
        self.delete_bt.setIcon(QIcon('assets/icons/cancel.svg'))
        bottom_buttons_layout.addWidget(self.delete_bt)
        self.delete_bt.font().setPointSize(10)
        self.delete_bt.setEnabled(False)
        self.findChild(QLineEdit, "name").textChanged.connect(
            self.ManageDeletePlayerFromDBActive)
        self.findChild(QLineEdit, "team").textChanged.connect(
            self.ManageDeletePlayerFromDBActive)
        self.delete_bt.clicked.connect(self.DeletePlayerFromDB)

        self.clear_bt = QPushButton("Clear")
        self.clear_bt.font().setPointSize(10)
        # self.clear_bt.setFont(self.parent.font_small)
        self.clear_bt.setIcon(QIcon('assets/icons/undo.svg'))
        bottom_buttons_layout.addWidget(self.clear_bt)
        self.clear_bt.clicked.connect(self.Clear)

        # Move up/down
        self.btMoveUp = QPushButton()
        self.btMoveUp.setMaximumWidth(32)
        self.btMoveUp.setIcon(QIcon("./assets/icons/arrow_up.svg"))
        bottom_buttons_layout.addWidget(self.btMoveUp)
        self.btMoveDown = QPushButton()
        self.btMoveDown.setMaximumWidth(32)
        self.btMoveDown.setIcon(QIcon("./assets/icons/arrow_down.svg"))
        bottom_buttons_layout.addWidget(self.btMoveDown)

        self.SetIndex(index, teamNumber)

        self.findChild(QLineEdit, "name").textChanged.connect(
            self.ExportMergedName)
        self.findChild(QLineEdit, "team").textChanged.connect(
            self.ExportMergedName)

        self.findChild(QLineEdit, "name").textChanged.connect(
            lambda x: self.ExportPlayerImages())
        self.findChild(QLineEdit, "team").textChanged.connect(
            lambda x: self.ExportPlayerImages())

        self.findChild(QLineEdit, "name").textChanged.connect(
            lambda x: self.ExportPlayerId())
        self.findChild(QLineEdit, "team").textChanged.connect(
            lambda x: self.ExportPlayerId())

        for c in self.findChildren(QLineEdit):
            c.textChanged.connect(
                lambda text, element=c: [
                    StateManager.Set(
                        f"{self.path}.{element.objectName()}", text)
                ])

        for c in self.findChildren(QComboBox):
            c.currentIndexChanged.connect(
                lambda text, element=c: [
                    StateManager.Set(
                        f"{self.path}.{element.objectName()}", element.currentData(
                        )
                    )
                ]
            )
            c.currentIndexChanged.emit(0)

        self.SetCharactersPerPlayer(1)

        TSHScoreboardPlayerWidget.signals.characters_changed.connect(
            self.ReloadCharacters)

        TSHPlayerDB.signals.db_updated.connect(
            self.SetupAutocomplete)
        self.SetupAutocomplete()

    def Delete(self):
        StateManager.Unset(self.path)

    def CharactersChanged(self):
        characters = {}

        for i, (element, character, color) in enumerate(self.character_elements):
            data = character.currentData()
            if character.currentData() == None:
                data = {"name": character.currentText()}

            data["assets"] = color.currentData()

            if data["assets"] == None:
                data["assets"] = {}

            data["skin"] = color.currentText()

            characters[i+1] = data

        StateManager.Set(
            f"{self.path}.character", characters)

    def SetLosers(self, value):
        self.losers = value
        self.ExportMergedName()

    def ExportMergedName(self):
        team = self.findChild(QLineEdit, "team").text()
        name = self.findChild(QLineEdit, "name").text()
        merged = ""

        if team != "":
            merged += team+" | "

        merged += name

        if self.losers:
            merged += " [L]"

        StateManager.Set(
            f"{self.path}.mergedName", merged)

    def ExportPlayerImages(self, onlineAvatar=None):
        team = self.findChild(QLineEdit, "team").text()
        name = self.findChild(QLineEdit, "name").text()
        merged = ""

        if team != "":
            merged += team+" "

        merged += name

        merged = merged.replace("/", " ")
        merged = merged.replace(":", " ")

        # Online avatar
        StateManager.Set(
            f"{self.path}.online_avatar", onlineAvatar)

        # Local avatar
        if os.path.exists(f"./user_data/player_avatar{merged}.png"):
            StateManager.Set(
                f"{self.path}.avatar", f"./user_data/player_avatar{merged}.png")
        else:
            StateManager.Set(
                f"{self.path}.avatar", None)

        # Sponsor logo
        if os.path.exists(f"./user_data/sponsor_logo/{team}.png"):
            StateManager.Set(
                f"{self.path}.sponsor_logo", f"./user_data/sponsor_logo/{team}.png")
        else:
            StateManager.Set(
                f"{self.path}.sponsor_logo", None)

    def ExportPlayerId(self, id=None):
        StateManager.Set(
            f"{self.path}.id", id)

    def SwapWith(self, other: "TSHScoreboardPlayerWidget"):
        tmpData = []

        # Save state
        for w in [self, other]:
            data = {}
            for widget in w.findChildren(QWidget):
                if type(widget) == QLineEdit:
                    data[widget.objectName()] = widget.text()
                if type(widget) == QComboBox:
                    data[widget.objectName()] = widget.currentIndex()
            data["online_avatar"] = StateManager.Get(
                f"{w.path}.online_avatar")
            data["id"] = StateManager.Get(
                f"{w.path}.id")
            tmpData.append(data)

        # Load state
        for i, w in enumerate([other, self]):
            for objName in tmpData[i]:
                widget = w.findChild(QWidget, objName)
                if widget:
                    if type(widget) == QLineEdit:
                        widget.setText(tmpData[i][objName])
                    if type(widget) == QComboBox:
                        widget.setCurrentIndex(tmpData[i][objName])
            QCoreApplication.processEvents()
            w.ExportPlayerImages(tmpData[i]["online_avatar"])
            w.ExportPlayerId(tmpData[i]["id"])

    def SetIndex(self, index: int, team: int):
        self.findChild(QWidget, "title").setText(f"Player {index}")
        self.index = index
        self.teamNumber = team

    def SetCharactersPerPlayer(self, number):
        while len(self.character_elements) < number:
            character_element = QWidget()
            character_element.setLayout(QHBoxLayout())
            character_element.layout().setSpacing(0)
            character_element.layout().setContentsMargins(0, 0, 0, 0)
            player_character = QComboBox()
            player_character.setEditable(True)
            character_element.layout().addWidget(player_character)
            player_character.setMinimumWidth(120)
            player_character.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            player_character.view().setMinimumWidth(250)
            player_character.completer().setCompletionMode(QCompleter.PopupCompletion)
            player_character.completer().popup().setMinimumWidth(250)
            player_character.setModel(TSHScoreboardPlayerWidget.characterModel)
            player_character.setIconSize(QSize(24, 24))
            player_character.setFixedHeight(32)

            player_character_color = QComboBox()
            character_element.layout().addWidget(player_character_color)
            player_character_color.setIconSize(QSize(48, 48))
            player_character_color.setFixedHeight(32)
            player_character_color.setMinimumWidth(120)
            view = QListView()
            view.setIconSize(QSize(64, 64))
            player_character_color.setView(view)
            # self.player_character_color.activated.connect(self.CharacterChanged)
            # self.CharacterChanged()
            self.character_container.layout().addWidget(character_element)

            self.character_elements.append(
                [character_element, player_character, player_character_color])

            player_character.currentIndexChanged.connect(
                lambda x, element=player_character, target=player_character_color: [
                    self.LoadSkinOptions(element, target),
                    self.CharactersChanged()
                ]
            )

            player_character_color.currentIndexChanged.connect(
                lambda index, element=player_character: [
                    self.CharactersChanged()
                ]
            )

            player_character.setCurrentIndex(0)
            player_character_color.setCurrentIndex(0)

            player_character.setObjectName(
                f"character_{len(self.character_elements)}")
            player_character_color.setObjectName(
                f"character_color_{len(self.character_elements)}")

        while len(self.character_elements) > number:
            self.character_elements[-1][0].setParent(None)
            self.character_elements.pop()

        self.CharactersChanged()

    def LoadCountries(self):
        try:
            if TSHScoreboardPlayerWidget.countryModel == None:
                countries_json = TSHCountryHelper.countries_json

                TSHScoreboardPlayerWidget.countries = {}

                for c in countries_json:
                    TSHScoreboardPlayerWidget.countries[c["iso2"]] = {
                        "name": c["name"],
                        "code": c["iso2"],
                        "latitude": c.get("latitude"),
                        "longitude": c.get("longitude"),
                        "states": {}
                    }

                    for s in c["states"]:
                        TSHScoreboardPlayerWidget.countries[c["iso2"]]["states"][s["state_code"]] = {
                            "code": s["state_code"],
                            "name": s["name"],
                            "latitude": s.get("latitude"),
                            "longitude": s.get("longitude"),
                        }

                TSHScoreboardPlayerWidget.countryModel = QStandardItemModel()

                noCountry = QStandardItem()
                noCountry.setData({}, Qt.ItemDataRole.UserRole)
                TSHScoreboardPlayerWidget.countryModel.appendRow(noCountry)

                for i, country_code in enumerate(TSHScoreboardPlayerWidget.countries.keys()):
                    item = QStandardItem()
                    item.setIcon(
                        QIcon(f'./assets/country_flag/{country_code.lower()}.png'))
                    countryData = {
                        "name": TSHScoreboardPlayerWidget.countries[country_code]["name"],
                        "code": TSHScoreboardPlayerWidget.countries[country_code]["code"],
                        "latitude": TSHScoreboardPlayerWidget.countries[country_code]["latitude"],
                        "longitude": TSHScoreboardPlayerWidget.countries[country_code]["longitude"],
                        "asset": f'./assets/country_flag/{country_code.lower()}.png'
                    }
                    item.setData(countryData, Qt.ItemDataRole.UserRole)
                    item.setData(
                        f'{TSHScoreboardPlayerWidget.countries[country_code]["name"]} ({country_code})', Qt.ItemDataRole.EditRole)
                    TSHScoreboardPlayerWidget.countryModel.appendRow(item)

            countryCompleter = QCompleter(
                TSHScoreboardPlayerWidget.countryModel)

            country: QComboBox = self.findChild(QComboBox, "country")
            country.setCompleter(countryCompleter)
            country.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            country.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            country.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            country.view().setMinimumWidth(300)
            country.completer().setCompletionMode(QCompleter.PopupCompletion)
            country.completer().popup().setMinimumWidth(300)
            country.setModel(TSHScoreboardPlayerWidget.countryModel)

            country.currentIndexChanged.connect(self.LoadStates)

            state: QComboBox = self.findChild(QComboBox, "state")
            state.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            state.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            state.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            state.view().setMinimumWidth(300)
            state.completer().setCompletionMode(QCompleter.PopupCompletion)
            state.completer().popup().setMinimumWidth(300)

        except Exception as e:
            print(e)
            exit()

    def LoadStates(self, index):
        country: QComboBox = self.findChild(QComboBox, "country")

        countryData = None
        if country.currentData(Qt.ItemDataRole.UserRole) != None:
            countryData = TSHScoreboardPlayerWidget.countries.get(country.currentData(
                Qt.ItemDataRole.UserRole).get("code"), {})

        stateModel = QStandardItemModel()

        noState = QStandardItem()
        noState.setData({}, Qt.ItemDataRole.UserRole)
        stateModel.appendRow(noState)

        states = countryData.get("states")

        if states is not None:
            for i, state_code in enumerate(states.keys()):
                item = QStandardItem()
                # Windows has some weird thing with files named CON.png. In case a state code is CON,
                # we try to load _CON.png instead
                path = f'./assets/state_flag/{countryData.get("code")}/{"_CON" if state_code == "CON" else state_code}.png'
                states[state_code].update({
                    "asset": path
                })
                item.setIcon(QIcon(path))
                item.setData(states[state_code], Qt.ItemDataRole.UserRole)
                item.setData(
                    f'{states[state_code]["name"]} ({state_code})', Qt.ItemDataRole.EditRole)
                stateModel.appendRow(item)

        state: QComboBox = self.findChild(QComboBox, "state")
        state.setModel(stateModel)
        state.setCurrentIndex(0)

    def LoadCharacters():
        class CharacterLoaderThread(QThread):
            def run(self):
                try:
                    TSHScoreboardPlayerWidget.characterModel = QStandardItemModel()

                    # Add one empty
                    item = QStandardItem("")
                    TSHScoreboardPlayerWidget.characterModel.appendRow(item)

                    for c in TSHGameAssetManager.instance.characters.keys():
                        item = QStandardItem()
                        item.setData(c, Qt.ItemDataRole.EditRole)
                        item.setIcon(
                            QIcon(QPixmap.fromImage(TSHGameAssetManager.instance.stockIcons[c][0]).scaledToWidth(
                                32, Qt.TransformationMode.SmoothTransformation))
                        )
                        data = {
                            "name": c,
                            "codename": TSHGameAssetManager.instance.characters[c].get("codename")
                        }
                        item.setData(data, Qt.ItemDataRole.UserRole)
                        TSHScoreboardPlayerWidget.characterModel.appendRow(
                            item)

                    TSHScoreboardPlayerWidget.characterModel.sort(0)

                    TSHScoreboardPlayerWidget.signals.characters_changed.emit()
                except:
                    print(traceback.format_exc())

        characterLoaderThread = CharacterLoaderThread(
            TSHGameAssetManager.instance)
        characterLoaderThread.start()

    def LoadSkinOptions(self, element, target):
        characterData = element.currentData()

        skins = {}

        if characterData:
            skins = TSHGameAssetManager.instance.skins.get(
                element.currentData().get("name"), {})

        sortedSkins = [int(k) for k in skins.keys()]
        sortedSkins.sort()

        target.clear()

        skinModel = QStandardItemModel()

        for skin in sortedSkins:
            assetData = TSHGameAssetManager.instance.GetCharacterAssets(
                element.currentData().get("codename"), skin)
            if assetData == None:
                assetData = {}
            item = QStandardItem()
            item.setData(str(skin), Qt.ItemDataRole.EditRole)
            item.setData(assetData, Qt.ItemDataRole.UserRole)

            # Set to use first asset as a fallback
            key = list(assetData.keys())[0]

            for k, asset in list(assetData.items()):
                if "portrait" in asset.get("type", []):
                    key = k
                    break
                if "icon" in asset.get("type", []):
                    key = k

            pix = QPixmap.fromImage(QImage(assetData[key]["asset"]))

            originalH = pix.height()

            pix = pix.scaledToWidth(
                64, Qt.TransformationMode.SmoothTransformation)

            if asset.get("eyesight", {}).get("y", 0):
                newImg = QImage(QSize(64, 48), QImage.Format.Format_RGBA64)
                newImg.fill(QColor(0, 0, 0, 0))
                painter = QPainter()
                painter.begin(newImg)

                moveY = 32/2 - \
                    asset.get("eyesight").get("y", 0)/originalH*pix.height()
                moveY = min(moveY, 16)
                moveY = max(moveY, -16)

                painter.drawPixmap(
                    0,
                    moveY,
                    pix
                )
                painter.end()

                pix = QPixmap.fromImage(newImg)

            item.setIcon(
                QIcon(pix)
            )
            skinModel.appendRow(item)

        target.setModel(skinModel)

    def ReloadCharacters(self):
        for c in self.character_elements:
            c[1].setModel(TSHScoreboardPlayerWidget.characterModel)
            c[1].setIconSize(QSize(24, 24))
            c[1].setFixedHeight(32)

    def SetupAutocomplete(self):
        if TSHPlayerDB.model:
            self.findChild(QLineEdit, "name").setCompleter(QCompleter())
            self.findChild(QLineEdit, "name").completer().activated[QModelIndex].connect(
                lambda x: self.SetData(x.data(Qt.ItemDataRole.UserRole)), Qt.QueuedConnection)
            self.findChild(QLineEdit, "name").completer().setCaseSensitivity(
                Qt.CaseSensitivity.CaseInsensitive)
            self.findChild(QLineEdit, "name").completer(
            ).setFilterMode(Qt.MatchFlag.MatchContains)
            self.findChild(QLineEdit, "name").completer().setModel(
                TSHPlayerDB.model)

            self.ManageSavePlayerToDBText()
            self.ManageDeletePlayerFromDBActive()

    def SetData(self, data, dontLoadFromDB=False, clear=True):
        if clear:
            self.Clear()

        # Load player data from DB; will be overwriten by incoming data
        if not dontLoadFromDB and clear:
            tag = data.get(
                "prefix")+" "+data.get("gamerTag") if data.get("prefix") else data.get("gamerTag")

            for i in range(TSHPlayerDB.model.rowCount()):
                item = TSHPlayerDB.model.item(i).data(Qt.ItemDataRole.UserRole)

                dbTag = item.get(
                    "prefix")+" "+item.get("gamerTag") if item.get("prefix") else item.get("gamerTag")

                if tag == dbTag:
                    self.SetData(item, dontLoadFromDB=True)

        if data.get("gamerTag"):
            self.findChild(QWidget, "name").setText(f'{data.get("gamerTag")}')

        if data.get("prefix"):
            self.findChild(QWidget, "team").setText(f'{data.get("prefix")}')

        if data.get("name"):
            self.findChild(QWidget, "real_name").setText(f'{data.get("name")}')

        if data.get("avatar"):
            self.ExportPlayerImages(data.get("avatar"))

        if data.get("id"):
            self.ExportPlayerId(data.get("id"))

        if data.get("twitter"):
            self.findChild(QWidget, "twitter").setText(
                f'{data.get("twitter")}')

        if data.get("country_code"):
            countryElement: QComboBox = self.findChild(
                QComboBox, "country")
            countryIndex = 0
            for i in range(self.countryModel.rowCount()):
                item = self.countryModel.item(
                    i).data(Qt.ItemDataRole.UserRole)
                if item:
                    if data.get("country_code") == item.get("code"):
                        countryIndex = i
                        break
            countryElement.setCurrentIndex(countryIndex)

        if data.get("state_code"):
            countryElement: QComboBox = self.findChild(
                QComboBox, "country")
            stateElement: QComboBox = self.findChild(QComboBox, "state")
            stateIndex = 0
            for i in range(stateElement.model().rowCount()):
                item = stateElement.model().item(i).data(Qt.ItemDataRole.UserRole)
                if item:
                    if data.get("state_code") == item.get("code"):
                        stateIndex = i
                        break
            stateElement.setCurrentIndex(stateIndex)

        if data.get("mains"):
            if type(data.get("mains")) == list:
                for element in self.character_elements:
                    character_element = element[1]
                    characterIndex = 0
                    for i in range(character_element.model().rowCount()):
                        item = character_element.model().item(i).data(Qt.ItemDataRole.UserRole)
                        if item:
                            if item.get("name") == data.get("mains")[0]:
                                characterIndex = i
                                break
                    character_element.setCurrentIndex(characterIndex)
            elif type(data.get("mains")) == dict:
                mains = data.get("mains").get(
                    TSHGameAssetManager.instance.selectedGame.get("codename"), [])

                for i, main in enumerate(mains):
                    if i < len(self.character_elements):
                        character_element = self.character_elements[i][1]
                        color_element = self.character_elements[i][2]
                        characterIndex = 0
                        for i in range(character_element.model().rowCount()):
                            item = character_element.model().item(i).data(Qt.ItemDataRole.UserRole)
                            if item:
                                if item.get("name") == main[0]:
                                    characterIndex = i
                                    break
                        character_element.setCurrentIndex(characterIndex)
                        color_element.setCurrentIndex(int(main[1]))

    def GetCurrentPlayerTag(self):
        gamerTag = self.findChild(QWidget, "name").text()
        prefix = self.findChild(QWidget, "team").text()
        return prefix+" "+gamerTag if prefix else gamerTag

    def SavePlayerToDB(self):
        tag = self.GetCurrentPlayerTag()

        playerData = {
            "prefix": self.findChild(QWidget, "team").text(),
            "gamerTag": self.findChild(QWidget, "name").text(),
            "name": self.findChild(QWidget, "real_name").text(),
            "twitter": self.findChild(QWidget, "twitter").text()
        }

        if TSHGameAssetManager.instance.selectedGame.get("codename"):
            mains = []

            for i, (element, character, color) in enumerate(self.character_elements):
                data = {}

                if character.currentData() is not None:
                    data["name"] = character.currentData().get("name")
                else:
                    data["name"] = ""

                data["skin"] = color.currentText()

                if data["skin"] == None:
                    data["skin"] = 0

                if data["name"] != "":
                    mains.append([data.get("name"), data.get("skin")])

            playerData["mains"] = {
                TSHGameAssetManager.instance.selectedGame.get("codename"): mains
            }

        if self.findChild(QComboBox, "country").currentData(Qt.ItemDataRole.UserRole):
            playerData["country_code"] = self.findChild(
                QComboBox, "country").currentData(Qt.ItemDataRole.UserRole).get("code")

        if self.findChild(QComboBox, "state").currentData(Qt.ItemDataRole.UserRole):
            playerData["state_code"] = self.findChild(
                QComboBox, "state").currentData(Qt.ItemDataRole.UserRole).get("code")

        TSHPlayerDB.AddPlayers([playerData], overwrite=True)

    def ManageSavePlayerToDBText(self):
        tag = self.GetCurrentPlayerTag()

        if tag in TSHPlayerDB.database:
            self.save_bt.setText("Update player")
        else:
            self.save_bt.setText("Save new player")

    def ManageDeletePlayerFromDBActive(self):
        tag = self.GetCurrentPlayerTag()

        if tag in TSHPlayerDB.database:
            self.delete_bt.setEnabled(True)
        else:
            self.delete_bt.setEnabled(False)

    def DeletePlayerFromDB(self):
        tag = self.GetCurrentPlayerTag()
        TSHPlayerDB.DeletePlayer(tag)

    def Clear(self):
        for c in self.findChildren(QLineEdit):
            c.setText("")

        for c in self.findChildren(QComboBox):
            c.setCurrentIndex(0)


TSHGameAssetManager.instance.signals.onLoad.connect(
    TSHScoreboardPlayerWidget.LoadCharacters)
