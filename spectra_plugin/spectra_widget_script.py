import os
from qgis.PyQt import uic, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget, QScrollArea, QGraphicsView, QGraphicsScene, QRubberBand, QApplication
from qgis.core import QgsProject, QgsMapLayer,QgsVectorLayer, QgsWkbTypes, QgsRasterLayer
from PyQt5.QtGui import QIcon, QWheelEvent, QPen, QCursor, QPixmap, QPainter, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRectF, QLineF, QRect, QSize


# First Tab (Menu Tab)
# ****************************************************************************************************
# Input Menu Group
# ----------------------------------------------------------------------------------------------------------
class InputImageMenu:
    def __init__(self, input_combo, parent=None):
        self.input_combo = input_combo
        self.parent = parent
        self.user_layers = []  # Store user-selected layers here
        

        # Connect to layer tree signals
        QgsProject.instance().layersAdded.connect(self.populate_raster_combo)
        QgsProject.instance().layersRemoved.connect(self.populate_raster_combo)
        self.populate_raster_combo()  # Initial population

    def populate_raster_combo(self):
        """Populate combo box with raster layers including user-selected ones."""
        current_layer = self.input_combo.currentData()
        self.input_combo.clear()

        # Get all raster layers from QGIS project
        raster_layers = [layer for layer in QgsProject.instance().mapLayers().values()
                         if isinstance(layer, QgsRasterLayer)]

        # Combine QGIS raster layers and user-selected layers
        all_layers = raster_layers + self.user_layers

        # Add placeholder at the top
        self.input_combo.addItem("...", None)

        # Add them to combo box
        for layer in all_layers:
            crs = layer.crs().authid() if layer.crs().isValid() else "Unknown CRS"
            file_path = os.path.join(os.path.dirname(__file__), 'raster layer logo.png')
            raster_icon = QIcon(file_path)
            label = f"[{crs}] {layer.name()}"
            self.input_combo.addItem(raster_icon, label, layer)


        # Restore previous selection if possible
        if current_layer:
            index = self.input_combo.findData(current_layer)
            if index >= 0:
                self.input_combo.setCurrentIndex(index)

    def browse_raster_file(self):
        """Browse for a raster file (GeoTIFF, etc.) without adding it to QGIS."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Raster File",
            "",
            "Raster Files (*.tif *.tiff)"
        )
        if not file_path:
            return

        layer_name = os.path.splitext(os.path.basename(file_path))[0]
        layer = QgsRasterLayer(file_path, layer_name)

        if not layer.isValid():
            QMessageBox.warning(self.parent, "Error", "Invalid raster file!")
            return

        # Do NOT add to QGIS project
        # QgsProject.instance().addMapLayer(layer)

        # Instead, store it in our list and refresh combo box
        self.user_layers.append(layer)
        self.populate_raster_combo()
        self.input_combo.setCurrentIndex(self.input_combo.findData(layer))

    def get_image(self):
        """Get the currently selected raster layer."""
        return self.input_combo.currentData()



class AOIMenu:
    def __init__(self, aoi_combo, parent=None):
        """
        Args:
            aoi_combo: The QComboBox to manage.
            parent: Parent widget (for dialogs).
        """
        self.aoi_combo = aoi_combo  # Assign the widget
        self.parent = parent  # Store parent for dialogs
        self.user_layers = []  # Store user-selected layers here

        # Connect to layer tree signals
        QgsProject.instance().layersAdded.connect(self.populate_aoi_combo)
        QgsProject.instance().layersRemoved.connect(self.populate_aoi_combo)
        self.populate_aoi_combo()  # Initial population

    def populate_aoi_combo(self):
        """Populate AOI combo with polygon layers (public method)."""
        current_layer = self.aoi_combo.currentData()
        self.aoi_combo.clear()
        # Combine QGIS raster layers and user-selected layers
        all_layers = list(QgsProject.instance().mapLayers().values()) + self.user_layers
        # Add placeholder at the top
        self.aoi_combo.addItem("...", None)

        for layer in all_layers:
            if (
                isinstance(layer, QgsVectorLayer) 
                and layer.geometryType() == QgsWkbTypes.PolygonGeometry
            ):
                crs = layer.crs().authid()
                file_path = os.path.join(os.path.dirname(__file__), 'polygon later symbol.png')
                raster_icon = QIcon(file_path)
                label = f"[{crs}] {layer.name()}"
                self.aoi_combo.addItem(raster_icon,label, layer)
        
        

        if self.aoi_combo.count() == 0:
            self.aoi_combo.addItem("...", None)

            # Restore previous selection if possible
        if current_layer:
            index = self.aoi_combo.findData(current_layer)
            if index >= 0:
                self.aoi_combo.setCurrentIndex(index)

    def browse_aoi_shapefile(self):
        """Browse for a shapefile mask (public method)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,  # Use parent widget
            "Select Mask Shapefile", 
            "", 
            "Shapefiles (*.shp)"
        )
        if not file_path:
            return

        layer = QgsVectorLayer(
            file_path, 
            os.path.splitext(os.path.basename(file_path))[0], 
            "ogr"
        )
        if not layer.isValid():
            QMessageBox.warning(self.parent, "Error", "Invalid shapefile!")
            return

        if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            QMessageBox.warning(self.parent, "Error", "Please select a polygon layer!")
            return

        # Do NOT add to QGIS project
        # QgsProject.instance().addMapLayer(layer)

        # Instead, store it in our list and refresh combo box
        self.user_layers.append(layer)
        self.populate_aoi_combo()
        self.aoi_combo.setCurrentIndex(self.aoi_combo.findData(layer))

    def get_aoi_mask(self):
        """Get currently selected AOI mask layer."""
        return self.aoi_combo.currentData()
    
# ----------------------------------------------------------------------------------------------------------



# Model Menu Group
# ----------------------------------------------------------------------------------------------------------
class ModelMenuGroup(QObject):
    """Manages dynamic model loading based on task selection (connects to existing UI widgets)."""
    
    model_changed = pyqtSignal(str)  # Emits when model changes (path/name)
    subtask_changed = pyqtSignal(str)

    def __init__(self, task_combo, subtask_combo, model_combo, explore_btn, param_groupbox, param_button, scrollarea,  parent = None):
        """
        Args:
            task_combo (QComboBox): Your existing task selection combo (Part 1)
            model_combo (QComboBox): Your existing model selection combo (Part 2)
            explore_btn (QPushButton): Your existing "Explore" button (Part 2)
        """
        super().__init__(parent)
        
        # Store references to existing UI widgets
        self.task_combo = task_combo
        self.model_combo = model_combo
        self.explore_btn = explore_btn
        self.menu = param_groupbox
        self.button = param_button
        self.scrollArea = scrollarea
        self.subtask_combo = subtask_combo

        # Adjusting scrollarea
        self.scrollArea.setSizeAdjustPolicy(QScrollArea.AdjustToContents)
        self.button.setArrowType(Qt.RightArrow)
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setCheckable(True)
        self.menu.setVisible(False)
        
        # Subtask database
        self.subtask_library = {
            "Detection": ["Building", "Tree"],
            "Classification": ["Land Use Land Cover", "Crop Type"]
        }

        # Model database (customize with your actual models later)
        self.model_library = {
            "Building": ["UNet", "DeepLabV3", "MaskRCNN"],
            "Tree": ["YOLOv5", "FasterRCNN", "SSD"],
            "Land Use Land Cover": ["LSTM", "Transformer", "ARIMA"],
            "Crop Type": ["ResNet50", "EfficientNet", "ViT"]
        }
        
        # Defining current variable
        # ============================================================================
        # Current subtask 
        self.current_subtask = self.subtask_library.copy()

        # Current models (can be replaced with real paths later)
        self.current_models = self.model_library.copy()
        # ============================================================================

        
        # Connecting signals
        # ============================================================================
        # Connect signals task 2 subtask
        self.task_combo.currentTextChanged.connect(self.update_subtask)

        # Connect signals subtask 2 model
        self.subtask_combo.currentTextChanged.connect(self.update_models)
        # ============================================================================
        # Initialize
        self.update_models(self.task_combo.currentText()) # for model
        self.update_subtask(self.task_combo.currentText()) # for subtask

        # For explore model button
        self.explore_btn.clicked.connect(self.browse_model)
        
        

    def update_subtask(self, task):
        """Updates subtask based on selected task."""
        self.subtask_combo.clear()
        
        subtask = self.current_subtask.get(task, [])
        if subtask:
            self.subtask_combo.addItems(subtask)
            self.subtask_changed.emit(subtask[0])  # Emit first model by default
        else:
            self.subtask_combo.addItem("...")

    def update_models(self, task):
        """Updates model_combo based on selected task."""
        self.model_combo.clear()
        
        models = self.current_models.get(task, [])
        if models:
            self.model_combo.addItems(models)
            self.model_changed.emit(models[0])  # Emit first model by default
        else:
            self.model_combo.addItem("...")

    def browse_model(self):
        """Opens file dialog and updates model list."""
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Select Model", "", "Model Files (*.pt *.pth *.h5 *.onnx)")
        
        if file_path:
            task = self.task_combo.currentText()
            model_name = os.path.basename(file_path)
            
            # Update model list (prepend custom model)
            if task in self.current_models:
                self.current_models[task].insert(0, file_path)
            else:
                self.current_models[task] = [file_path]
            
            # Refresh and select the new model
            self.update_models(task)
            self.model_combo.setCurrentText(file_path)

    def add_model_paths(self, task_model_dict):
        """Inject real model paths when available.
        Args:
            task_model_dict (dict): e.g., {"Segmenting": ["/path/to/model1.pth"]}
        """
        for task, paths in task_model_dict.items():
            self.current_models[task] = paths
        self.update_models(self.task_combo.currentText())

    def get_current_model(self):
        """Returns the selected model path/name."""
        return self.model_combo.currentText()

    def show_text1():
            QMessageBox.information(None, "Info", "Batch size is used to determine "
            "how many images processed at a single runtime. " 
            "Leave it by default if you only want to process a single image.")

    def show_text2():
            QMessageBox.information(None, "Info", "Patch size is how big each piece " \
            "of image is when processed. Smaller patches (like 32 or 64) run faster and " \
            "use less memory—good for weak GPUs. Larger patches (like 128 or 256) give " \
            "better results but need more GPU memory. If the program crashes, lower the " \
            "patch size. If your GPU is strong, try larger sizes for better quality. Start " \
            "at 128 and adjust up or down based on speed and stability." \
            "\n\n* Note: Only models like " \
            "Vision Transformers (ViT, Swin, etc.) use patching. CNNs (e.g., ResNet) don’t use " \
            "patch size and process the full image directly. So, skip this field!")    
    
    def show_text3():
            QMessageBox.information(None, "Info", "This field is used to sets the size " \
            "of the image fed into the model. Lower resolution (e.g., 128×128) speeds " \
            "up processing and reduces memory use, ideal for weaker hardware. Higher " \
            "resolution (e.g., 512×512 or more) improves detail and accuracy but demands " \
            "more GPU/CPU power. Adjust based on your hardware and accuracy needs.")

    def show_text4():
            msg = """
            ● Present : Analyze current image data <br>
            <br>
            ● Change Detection : Compare images from two dates <br>
            <br>
            ●  Prediction : Predict future conditions from past data <br>
            <br>
            * Note: Only Present Time Mode available right now, <br>
            &nbsp;&nbsp;&nbsp;&nbsp;Change Detection and Prediction are still under<br>
            &nbsp;&nbsp;&nbsp;&nbsp;development
            """
            QMessageBox.information(None, "Info", msg)

    def show_text5():
        msg = """
        ● Detection: Identify and locate specific targets (water bodies, <br>
        &nbsp;&nbsp;&nbsp;&nbsp;vehicles, trees, hssj etc.) in image.
        <br><br>
        ● Classification: Categorize all elements in the image based on <br>
        &nbsp;&nbsp;&nbsp;&nbsp;defined classes/groups
        """
        QMessageBox.information(None, "Info", msg)

    def show_text6():
           
            msg = """
            Choose your preferred file format (JPG, PNG, etc.) before selecting the file<br>
            name and directory. If You have select the file directory and name but dont<br> 
            want to use your preselected format, You can change it later by simply<br>
            select another format in the  format menu, the file format then will<br>
            be updated automatically without reopening the file explorer!
            <br>
            """
            QMessageBox.information(None, "Info", msg)

    def setup_menu_toggle(self):
        is_visible = not self.menu.isVisible()
        self.menu.setVisible(is_visible)
        self.button.setArrowType(Qt.DownArrow if is_visible else Qt.RightArrow)

    # ----------------------------------------------------------------------------------------------------------




    # Export Menu Group
    # ----------------------------------------------------------------------------------------------------------
class ExportMenuGroup(QWidget):
    def __init__(self, lineedit, combobox, parent=None):
        super().__init__(parent)
        self.lineEdit = lineedit
        self.combobox = combobox
        self.lineEdit.setPlaceholderText(" Create temporary file !")
        
        # Connect combobox change signal
        self.combobox.currentTextChanged.connect(self.update_extension)

    def update_extension(self, new_format_text):
        """Update file extension when format combobox changes"""
        current_path = self.lineEdit.text()
        if current_path:  # Only update if there's already a path
            # Extract format name from combobox text
            selected_format = new_format_text.split(' :')[0].split(' (')[0]
            
            # Get format mapping
            format_map = self.get_format_map()
            
            if selected_format in format_map:
                default_ext = format_map[selected_format][0]
                # Remove old extension and add new one
                base_path = os.path.splitext(current_path)[0]
                new_path = f"{base_path}{default_ext}"
                self.lineEdit.setText(new_path)

    def get_format_map(self):
        """Return the format mapping dictionary"""
        return {
            "GeoTIFF": (".tif", "GeoTIFF (*.tif *.tiff)"),
            "JPEG2000": (".jp2", "JPEG2000 (*.jp2)"),
            "PNG": (".png", "PNG (*.png)"),
            "JPEG": (".jpg", "JPEG (*.jpg *.jpeg)"),
            "BMP": (".bmp", "BMP (*.bmp)"),
            "TIFF": (".tiff", "TIFF (*.tiff)"),
            "PDF": (".pdf", "PDF (*.pdf)"),
            "Shapefile": (".shp", "Shapefile (*.shp)"),
            "GeoJSON": (".geojson", "GeoJSON (*.geojson)"),
            "KML/KMZ": (".kml", "KML/KMZ (*.kml *.kmz)"),
            "GPKG": (".gpkg", "GeoPackage (*.gpkg)"),
            "DXF": (".dxf", "DXF (*.dxf)")
        }

    def select_export_path(self):
        """Open file dialog with format determined by the format combobox selection"""
        # Extract format name from combobox text
        selected_text = self.combobox.currentText()
        selected_format = selected_text.split(' :')[0].split(' (')[0]
        
        # Get format mapping
        format_map = self.get_format_map()
        
        # Get the extension and filter for the selected format
        if selected_format in format_map:
            default_ext, file_filter = format_map[selected_format]
        else:
            default_ext, file_filter = ".tif", "All Files (*)"
        
        # Open file dialog
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Export Location",
            self.lineEdit.text() or "",
            file_filter
        )
        
        if path:
            # Add extension if not already present
            if not any(path.lower().endswith(ext[0]) for ext in format_map.values()):
                path += default_ext
            
            self.lineEdit.setText(path)
    # ----------------------------------------------------------------------------------------------------------

# **************************************************************************************************************



# Second Tab (Log Tab)
# **************************************************************************************************************
class TabLogWidget(QWidget):
    def __init__(self, logtext, tab, parent=None):
        super().__init__(parent)
        self.log_text_edit = logtext
        self.widgettab = tab

        # self.setup_connections()

    def change_tab(self):
        self.widgettab.setCurrentIndex(0)

    def clear_log(self):
        log_text = self.log_text_edit.toPlainText()
        if not log_text:
            QMessageBox.information(self,"No Log", "There is no log to clear.")
            return
        self.log_text_edit.clear()

    def copy_log(self):
        log_text = self.log_text_edit.toPlainText()
        if not log_text:
            QMessageBox.information(self,"No Log", "There is no log to copy.")
            return
        self.log_text_edit.selectAll()
        self.log_text_edit.copy()
        cursor = self.log_text_edit.textCursor()
        cursor.clearSelection()
        self.log_text_edit.setTextCursor(cursor)

    def export_log(self):
        log_text = self.log_text_edit.toPlainText()
        if not log_text:
            QMessageBox.information(self,"No Log", "There is no log to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            with open(file_path, 'w') as f:
                f.write(log_text)

# *************************************************************************************************************



# Graphics View
# **************************************************************************************************************

class CustomGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Create cursors
        self.hand_cursor = QCursor(Qt.OpenHandCursor)
        self.zoom_in_cursor = QCursor(QPixmap("C:/Users/Faruq/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/spectra_plugin/zoom in icon.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.zoom_out_cursor = QCursor(QPixmap("C:/Users/Faruq/AppData/Roaming/QGIS/QGIS3/profiles/default/python/plugins/spectra_plugin/zoom out icon.png").scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._zoom_mode = None
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self._origin = None
        


        # Create scene with a test plus sign
        scene = QGraphicsScene(self) # replace this with actual image if plugin ready to launch
        pen = QPen(Qt.red, 2)
        scene.addLine(QLineF(-20, 0, 20, 0), pen)  # horizontal
        scene.addLine(QLineF(0, -20, 0, 20), pen)  # vertical
        
        scene.setSceneRect(-1000, -1000, 2000, 2000)  # Center (0,0) in scene
        self.fitInView(0, 0, 1, 1)  # Optionally, zoom to center on startup
        self.initial_transform = self.transform().inverted()[0]
        self.setScene(scene)

       
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        

    def set_zoom_in_mode(self):
        self._zoom_mode = 'in'
        self.setCursor(self.zoom_in_cursor)
        self.viewport().setCursor(self.zoom_in_cursor)

    def set_zoom_out_mode(self):
        self._zoom_mode = 'out'
        self.setCursor(self.zoom_out_cursor)
        self.viewport().setCursor(self.zoom_out_cursor)

    def set_pan_mode(self):
        self._zoom_mode = None
        self._mouse_pressed = False
        self._pan_start_scene = None
        self.setDragMode(QGraphicsView.ScrollHandDrag) # prevent offset after zoom
        self.setCursor(self.hand_cursor)
        self.viewport().setCursor(self.hand_cursor)


    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.25 if not (event.modifiers() & Qt.ControlModifier) else 1.05
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        

    def mousePressEvent(self, event):
        if not self._zoom_mode and event.button() == Qt.LeftButton:
            self._mouse_pressed = True
            self._pan_start_scene = self.mapToScene(event.pos())
            self.viewport().setCursor(Qt.ClosedHandCursor)

        elif self._zoom_mode:
            # Zoom mode: use left click for rubber band
            if event.button() == Qt.LeftButton:
                self._origin = event.pos()
                self._rubber_band.setGeometry(QRect(self._origin, QSize()))
                self._rubber_band.show()
                self.setDragMode(QGraphicsView.NoDrag)

        elif (event.pos() - self._origin).manhattanLength() < 1:
            factor = 2.0 if self._zoom_mode == 'in' else 0.5
            self.scale(factor, factor)
            self.viewport().update()
            QApplication.processEvents()
            self._origin = None
        
        else:
            # Hand mode: left button for drag
            if event.button() == Qt.LeftButton:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
                self._mouse_pressed = True
                self._drag_pos = event.pos()
                self.viewport().setCursor(Qt.ClosedHandCursor)
        
        super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        if not self._zoom_mode and getattr(self, "_mouse_pressed", False):
            new_scene_pos = self.mapToScene(event.pos())
            delta = self._pan_start_scene - new_scene_pos
            self._pan_start_scene = self.mapToScene(event.pos())
            self.translate(delta.x(), delta.y())
        elif self._origin:
            rect = QRect(self._origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)
        super().mouseMoveEvent(event)


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._zoom_mode and self._origin:
                # Check if it was a click (not drag)
                if (event.pos() - self._origin).manhattanLength() < 1:
                    factor = 2.0 if self._zoom_mode == 'in' else 0.5
                    self.scale(factor, factor)
                else:
                    # It was a drag – do rubber band zoom
                    rect = self._rubber_band.geometry()
                    if rect.width() > 5:
                        scene_rect = self.mapToScene(rect).boundingRect()
                        if self._zoom_mode == 'in':
                            self.fitInView(scene_rect, Qt.KeepAspectRatio)
                        elif self._zoom_mode == 'out':
                             self.scale(0.7, 0.7)
                            # margin = 50
                            # inv_rect = self.sceneRect().adjusted(margin, margin, -margin, -margin)
                            # self.fitInView(inv_rect, Qt.KeepAspectRatio)
                self._rubber_band.hide()
                self._origin = None
            elif not self._zoom_mode:
                self._mouse_pressed = False
                self.viewport().setCursor(Qt.OpenHandCursor)

        super().mouseReleaseEvent(event)
    
    def reset_view(self):
        self.setTransform(self.initial_transform)
        self.centerOn(0, 0)  # Reset position to center at origin

    def zoom_full_extent(self):
        self.setTransform(self.initial_transform)
        self.centerOn(0, 0)
# **************************************************************************************************************